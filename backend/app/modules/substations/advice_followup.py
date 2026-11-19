"""Stage 9e-3/9e-4: turn advice into a follow-up with a frozen before/after plan, and apply a
finished swap to the master. The server recomputes the plan; client numbers are never trusted."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import get_db
from ..org_units.context import UnitContext, unit_context
from . import advice_service as svc
from .common import TRAFO_FIELDS, audit, data_units, dump, master_context
from .followup_models import PRIORITIES, GarduFollowup
from .followup_router import type_names, view
from .models import Substation, SubstationMasterHistory

router = APIRouter(prefix='/api/substations/advice-followups', tags=['Gardu Saran'])
KINDS = {'swap': 'tukar_trafo', 'move': 'pindah_beban'}
OPEN = ('terbuka', 'dikerjakan')


class PlanBody(BaseModel):
    substation_id: int = Field(ge=1)
    kind: str = Field(pattern='^(swap|move)$')
    target_id: int = Field(ge=1)
    line_no: int | None = Field(default=None, ge=1, le=5)
    portion: int | None = Field(default=None, ge=1, le=100)
    measurement_id: int | None = Field(default=None, ge=1)
    note: str | None = Field(default=None, max_length=2000)
    priority: str = 'sedang'
    assignee: str | None = Field(default=None, max_length=150)
    due_on: date | None = None


class ApplyBody(BaseModel):
    effective_on: date
    expected_version: int = Field(ge=1)
    confirm: bool


def compact(side):
    pick = lambda e: {'persen': e['persen'], 'beban_kva': e['beban_kva'], 'overload': e['overload'],
                      'category': e['category'] and e['category']['name']}
    return {'id': side['id'], 'code': side['code'], 'name': side['name'],
            'kva_before': side['kva_before'], 'kva_after': side['kva_after'],
            'phase_before': side['phase_before'], 'phase_after': side['phase_after'],
            'before': pick(side['before']), 'after': pick(side['after']),
            'lines_before': side['lines_before'], 'lines_after': side['lines_after']}


def default_note(kind, sides, line, portion):
    x, z = sides[0], sides[1]
    if kind == 'swap':
        return (f"Tukar trafo {x['code']} ({x['kva_before']:g} kVA) dengan {z['code']} ({z['kva_before']:g} kVA). "
                f"Perkiraan beban {x['code']} {x['before']['persen']:.1f}% menjadi {x['after']['persen']:.1f}%, "
                f"{z['code']} {z['before']['persen']:.1f}% menjadi {z['after']['persen']:.1f}%.")
    return (f"Pindahkan sekitar {portion}% beban jurusan {line} dari {x['code']} ke {z['code']}. "
            f"Perkiraan beban {x['code']} {x['before']['persen']:.1f}% menjadi {x['after']['persen']:.1f}%, "
            f"{z['code']} {z['before']['persen']:.1f}% menjadi {z['after']['persen']:.1f}%.")


@router.post('')
def create_plan(body: PlanBody, db: Session = Depends(get_db),
                ctx: UnitContext = Depends(unit_context('write_data'))):
    if body.priority not in PRIORITIES:
        raise HTTPException(422, 'Prioritas harus rendah, sedang, atau tinggi')
    station = svc.visible_station(db, ctx, body.substation_id)
    if station.unit_id not in data_units(db, ctx):
        raise HTTPException(403, 'Hanya unit pemilik gardu atau ULP induknya yang dapat membuat tindak lanjut')
    if body.kind == 'move' and (body.line_no is None or body.portion is None):
        raise HTTPException(422, 'Pindah beban memerlukan jurusan dan porsi')
    result = svc.review(db, ctx, station.id, body.kind, body.target_id, body.line_no, body.portion, body.measurement_id)
    if not result['source']['category'] or result['sides'][0]['before']['overload'] is not True:
        raise HTTPException(422, 'Gardu ini tidak overload menurut kategori yang berlaku')
    if not result['ok_after']:
        raise HTTPException(422, 'Rencana ini belum menghilangkan overload pada kedua gardu')
    type_code = KINDS[body.kind]
    duplicate = db.query(GarduFollowup).filter(
        GarduFollowup.substation_id == station.id, GarduFollowup.type_code == type_code,
        GarduFollowup.status.in_(OPEN)).all()
    if any((f.plan or {}).get('target_id') == body.target_id for f in duplicate):
        raise HTTPException(409, 'Sudah ada tindak lanjut serupa yang masih terbuka untuk gardu ini')
    sides = [compact(s) for s in result['sides']]
    plan = {'kind': body.kind, 'target_id': body.target_id, 'target_code': sides[1]['code'],
            'line_no': body.line_no, 'portion': body.portion, 'range': [result['option'].get('p_min'),
            result['option'].get('p_max')] if body.kind == 'move' else None,
            'basis': {'source_measurement_on': result['source']['measured_on'], 'source_session': result['source']['session'], 'target_session': result['target']['session'],
                      'target_measurement_on': result['target']['measured_on'],
                      'source_state': result['source']['state'], 'target_state': result['target']['state']},
            'sides': sides, 'created_on': date.today().isoformat(), 'applied': None}
    row = GarduFollowup(unit_id=station.unit_id, substation_id=station.id,
                        measurement_id=body.measurement_id, type_code=type_code,
                        note=(body.note or '').strip() or default_note(body.kind, sides, body.line_no, body.portion),
                        priority=body.priority, status='terbuka', assignee=(body.assignee or '').strip() or None,
                        due_on=body.due_on, plan=plan, created_by=ctx.actor.id, updated_by=ctx.actor.id)
    db.add(row)
    db.flush()
    audit(db, ctx, 'gardu_followup', row.id, None, dump(row), source='advice')
    db.commit()
    return view(row, station, type_names(db))


def swap_values(a, b):
    return {k: getattr(b, k) for k in TRAFO_FIELDS}, {k: getattr(a, k) for k in TRAFO_FIELDS}


@router.post('/{followup_id}/apply-swap')
def apply_swap(followup_id: int, body: ApplyBody, db: Session = Depends(get_db),
               ctx: UnitContext = Depends(master_context())):
    row = db.get(GarduFollowup, followup_id)
    allowed = data_units(db, ctx)
    if row is None or row.unit_id not in allowed:
        raise HTTPException(404, 'Tindak lanjut tidak ditemukan pada unit aktif')
    plan = row.plan or {}
    if row.type_code != KINDS['swap'] or plan.get('kind') != 'swap':
        raise HTTPException(422, 'Hanya tindak lanjut Tukar trafo yang dapat diterapkan ke master')
    if row.status != 'selesai':
        raise HTTPException(409, 'Ubah status menjadi Selesai lebih dulu, setelah pekerjaan fisiknya dilakukan')
    if plan.get('applied'):
        raise HTTPException(409, 'Tukar trafo ini sudah diterapkan ke master')
    if not body.confirm:
        raise HTTPException(422, 'Konfirmasi diperlukan')
    if body.expected_version != row.version:
        raise HTTPException(409, 'Tindak lanjut sudah diubah pengguna lain. Muat ulang.')
    if body.effective_on > date.today():
        raise HTTPException(422, 'Tanggal berlaku tidak boleh di masa depan')
    x, z = db.get(Substation, row.substation_id), db.get(Substation, plan.get('target_id') or 0)
    if x is None or z is None or x.unit_id not in allowed or z.unit_id not in allowed:
        raise HTTPException(403, 'Kedua gardu harus berada pada unit aktif atau KP di bawahnya')
    sx, sz = plan['sides'][0], plan['sides'][1]
    if (float(x.power_kva), x.phase) != (sx['kva_before'], sx['phase_before']) or \
            (float(z.power_kva), z.phase) != (sz['kva_before'], sz['phase_before']):
        raise HTTPException(409, 'Data trafo sudah berubah sejak rencana dibuat. Buat rencana baru.')
    before_x, before_z, before_row = dump(x), dump(z), dump(row)
    to_x, to_z = swap_values(x, z)
    for station, values in ((x, to_x), (z, to_z)):
        for key, value in values.items():
            setattr(station, key, value)
    db.flush()
    for station, before in ((x, before_x), (z, before_z)):
        after = dump(station)
        delta = {k: {'from': before[k], 'to': after[k]} for k in TRAFO_FIELDS if before[k] != after[k]}
        if delta:
            station.updated_by = ctx.actor.id
            db.add(SubstationMasterHistory(substation_id=station.id, effective_on=body.effective_on,
                                           changed_by=ctx.actor.id, changes=delta))
        audit(db, ctx, 'substation_master_update', station.code, before, after,
              reason='tukar trafo', followup_id=row.id)
    row.plan = {**plan, 'applied': {'on': date.today().isoformat(), 'effective_on': body.effective_on.isoformat(),
                                    'by': ctx.actor.id}}
    row.version, row.updated_by = row.version + 1, ctx.actor.id
    db.flush()
    audit(db, ctx, 'gardu_followup', row.id, before_row, dump(row), applied_swap=True)
    db.commit()
    return {'followup': view(row, x, type_names(db)), 'masters': [dump(x), dump(z)]}
