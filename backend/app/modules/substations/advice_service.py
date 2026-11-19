"""Stage 9e: loads gardu + latest measurements and runs the pure advice engine. Read-only."""
from datetime import date
from fastapi import HTTPException
from sqlalchemy import func
from ..org_units.models import OrgUnit
from . import advice_engine as eng
from .calculation_service import compute, context, prepare
from .common import child_ids, ulp_of
from .models import Substation, SubstationMeasurement, SubstationValue

EXAMINE_CAP = 200
DISCLAIMER = [
    'Ini saran berdasarkan pengukuran terakhir tiap sesi (dipakai sesi dengan beban tertinggi, seperti Analisa), bukan keputusan teknis.',
    'Impedansi, jatuh tegangan, susut, jarak jaringan, dan kemungkinan pekerjaan di lapangan tidak dihitung.',
    'Jarak adalah jarak garis lurus berdasarkan koordinat, bukan panjang jaringan.',
    'Pertumbuhan beban tidak diperhitungkan. Lakukan survei sebelum memutuskan.',
]


def family_units(db, ctx, station):
    ulp = ulp_of(db, db.get(OrgUnit, station.unit_id))
    ids = {station.unit_id}
    if ulp is not None:
        ids = {ulp.id} | {r[0] for r in db.query(OrgUnit.id).filter(
            OrgUnit.parent_id == ulp.id, OrgUnit.active.is_(True))}
    return ids & set(child_ids(db, ctx))


def visible_station(db, ctx, station_id):
    row = db.get(Substation, station_id)
    if row is None or row.unit_id not in child_ids(db, ctx):
        raise HTTPException(404, 'Gardu tidak ditemukan')
    return row


def latest_by_session(db, station_ids):
    """Latest measurement of every session per gardu, like Analisa's default selection."""
    if not station_ids:
        return {}
    rn = func.row_number().over(
        partition_by=(SubstationMeasurement.substation_id, SubstationMeasurement.session),
        order_by=(SubstationMeasurement.measured_on.desc(), SubstationMeasurement.id.desc())).label('rn')
    sub = db.query(SubstationMeasurement.id.label('mid'), rn).filter(
        SubstationMeasurement.substation_id.in_(list(station_ids))).subquery()
    rows = db.query(SubstationMeasurement).join(sub, SubstationMeasurement.id == sub.c.mid).filter(
        sub.c.rn == 1).all()
    out = {}
    for m in rows:
        out.setdefault(m.substation_id, []).append(m)
    return out


def all_measurements(groups):
    return [m for ms in groups.values() for m in ms]


class Assessor:
    """Evaluates nodes with the normal formula engine; the threshold is the admin's rule."""

    def __init__(self, db, measurements):
        self.db, self.conf = db, prepare(db)
        cells = {m.id: [] for m in measurements}
        if cells:
            for v in db.query(SubstationValue).filter(SubstationValue.measurement_id.in_(list(cells))):
                cells[v.measurement_id].append(v)
        self.conf['cells'] = cells

    def node(self, station, m, distance=None):
        variables, _, _, _ = context(self.db, m, self.conf)
        lines = {no: {c: variables.get(f'{c}_j{no}') for c in eng.CURRENT_CODES}
                 for no in range(1, m.snapshot_line_count + 1)}
        return {'id': station.id, 'code': station.code, 'name': station.name, 'm': m,
                'kva': float(station.power_kva), 'phase': int(station.phase),
                'line_count': m.snapshot_line_count, 'lines': lines, 'distance_km': distance,
                'labels': list(station.line_labels or []), 'unit_id': station.unit_id,
                'lat': station.lat and float(station.lat), 'lon': station.lon and float(station.lon)}

    def pick(self, station, measurements, distance=None, prefer_id=None):
        """The measurement Analisa would show: the session with the highest load (NULL never wins).
        When the caller names one (the one on screen), that exact measurement is used."""
        nodes = [self.node(station, m, distance) for m in measurements]
        if prefer_id is not None:
            chosen = [n for n in nodes if n['m'].id == prefer_id]
            if not chosen:
                raise HTTPException(422, 'Pengukuran bukan milik gardu ini')
            return chosen[0], self.evaluate(chosen[0])
        scored = [(n, self.evaluate(n)) for n in nodes]
        scored.sort(key=lambda item: (item[1]['persen'] is None, -(item[1]['persen'] or 0),
                                      item[0]['m'].measured_on.toordinal() * -1, -item[0]['m'].id))
        return scored[0]

    def evaluate(self, node, adjust=None):
        base = eng.trafo_adjust(node['kva'], node['phase'])

        def both(variables, aggregates):
            base(variables, aggregates)
            if adjust:
                adjust(variables, aggregates)
        result = compute(self.db, node['m'], prepared=self.conf, adjust=both)
        cols = {c['code']: c['value'] for c in result['columns']}
        cats = [x for x in result['matches'] if x['kind'] == 'category']
        main = next((c for c in cats if c['group_name'] == 'Pembebanan'), cats[0] if cats else None)
        persen = cols.get('persen_beban')
        return {'persen': persen, 'beban_kva': cols.get('beban_kva'),
                'tak_seimbang': cols.get('tak_seimbang'), 'kva': node['kva'],
                'overload': None if persen is None else any(c['code'] == eng.OVERLOAD_CODE for c in cats),
                'category': main and {'code': main['code'], 'name': main['name'], 'color': main['color']}}


def target_info(node, ev, today=None):
    m = node['m']
    return {'id': node['id'], 'code': node['code'], 'name': node['name'],
            'distance_km': None if node['distance_km'] is None else round(node['distance_km'], 2),
            'kva': node['kva'], 'phase': node['phase'], 'persen_now': ev['persen'],
            'category': ev['category'], 'measured_on': m.measured_on.isoformat(), 'session': m.session, 'state': m.state,
            'age_days': ((today or date.today()) - m.measured_on).days}


def load_pair(db, ctx, station, target_id=None, measurement_id=None):
    """Nodes for the source and (optionally) one target in its ULP, each on its worst recent session."""
    groups = latest_by_session(db, [station.id] + ([target_id] if target_id else []))
    if station.id not in groups:
        raise HTTPException(422, 'Gardu ini belum punya pengukuran')
    assessor = Assessor(db, all_measurements(groups))
    if measurement_id is not None:
        extra = db.get(SubstationMeasurement, measurement_id)
        if extra is None or extra.substation_id != station.id:
            raise HTTPException(422, 'Pengukuran bukan milik gardu ini')
        if extra.id not in {m.id for m in groups[station.id]}:
            groups[station.id].append(extra)
            assessor = Assessor(db, all_measurements(groups))
    x, ev_x = assessor.pick(station, groups[station.id], prefer_id=measurement_id)
    z = ev_z = None
    if target_id:
        target = db.get(Substation, target_id)
        if target is None or target.unit_id not in family_units(db, ctx, station) or \
                not target.active or target.id == station.id:
            raise HTTPException(404, 'Gardu tujuan tidak ditemukan pada ULP yang sama')
        if target.id not in groups:
            raise HTTPException(422, 'Gardu tujuan belum punya pengukuran')
        if target.lat is None or target.lon is None or station.lat is None or station.lon is None:
            raise HTTPException(422, 'Koordinat gardu belum lengkap')
        z, ev_z = assessor.pick(target, groups[target.id], eng.distance_km(
            float(station.lat), float(station.lon), float(target.lat), float(target.lon)))
    return assessor, x, ev_x, z, ev_z


def advice(db, ctx, station_id, radius_km=None, limit=8, measurement_id=None, today=None):
    station = visible_station(db, ctx, station_id)
    out = {'station_id': station.id, 'code': station.code, 'name': station.name,
           'disclaimer': DISCLAIMER, 'available': False, 'reason': None, 'overload': None,
           'basis': None, 'excluded': {}, 'swap': [], 'move': []}
    groups = latest_by_session(db, [station.id])
    if station.id not in groups:
        out['reason'] = 'Gardu ini belum punya pengukuran'
        return out
    if measurement_id is not None:
        extra = db.get(SubstationMeasurement, measurement_id)
        if extra is None or extra.substation_id != station.id:
            raise HTTPException(422, 'Pengukuran bukan milik gardu ini')
        if extra.id not in {m.id for m in groups[station.id]}:
            groups[station.id].append(extra)
    assessor = Assessor(db, all_measurements(groups))
    x, ev0 = assessor.pick(station, groups[station.id], prefer_id=measurement_id)
    m = x['m']
    out['basis'] = {'measurement_id': m.id, 'measured_on': m.measured_on.isoformat(), 'session': m.session,
                    'state': m.state, 'age_days': ((today or date.today()) - m.measured_on).days,
                    'persen': ev0['persen'], 'beban_kva': ev0['beban_kva'], 'kva': x['kva'],
                    'category': ev0['category'],
                    'kva_changed': abs(float(m.snapshot_power_kva) - x['kva']) > 1e-9}
    if ev0['overload'] is None:
        out['reason'] = 'Beban gardu ini tidak dapat dinilai (arus belum lengkap)'
        return out
    out['available'], out['overload'] = True, ev0['overload']
    if not ev0['overload']:
        out['reason'] = 'Gardu ini tidak overload menurut kategori yang berlaku'
        return out
    if station.lat is None or station.lon is None:
        out.update(available=False, reason='Gardu ini belum punya koordinat; isi di Master')
        return out
    pool = _candidates(db, ctx, station, radius_km, out)
    cand = latest_by_session(db, [s.id for s, _ in pool])
    assessor = Assessor(db, all_measurements(cand) + all_measurements(groups))
    x = assessor.node(station, m)
    ready = []
    for st, dist in pool:
        if st.id not in cand:
            out['excluded']['tanpa_pengukuran'] = out['excluded'].get('tanpa_pengukuran', 0) + 1
            continue
        node, ev = assessor.pick(st, cand[st.id], dist)
        if ev['overload'] is None:
            out['excluded']['tidak_dapat_dinilai'] = out['excluded'].get('tidak_dapat_dinilai', 0) + 1
            continue
        ready.append((node, ev))
    ready = ready[:max(1, min(limit, 20))]
    out['examined'] = len(pool)
    for node, ev in ready:
        info = target_info(node, ev, today)
        if node['phase'] != x['phase']:
            out['excluded']['fase_berbeda_untuk_tukar'] = out['excluded'].get('fase_berbeda_untuk_tukar', 0) + 1
        else:
            out['swap'].append({'target': info, **eng.swap_option(assessor.evaluate, x, node)})
        if ev['overload']:
            out['excluded']['sudah_overload_untuk_pindah'] = out['excluded'].get('sudah_overload_untuk_pindah', 0) + 1
            continue
        for line in eng.movable_lines(x):
            label = x['labels'][line - 1] if line <= len(x['labels']) else f'Jurusan {line}'
            out['move'].append({'target': info, 'line_no': line, 'line_label': label,
                                **eng.move_option(assessor.evaluate, x, node, line)})
    out['swap'].sort(key=lambda o: (not o['feasible'],
                                    max(v for v in (o.get('x_after'), o.get('z_after'), 0) if v is not None),
                                    o['target']['distance_km']))
    out['move'].sort(key=lambda o: (not o['feasible'], o['target']['distance_km'], o.get('p_min') or 101))
    out['move'] = out['move'][:30]
    return out


def _candidates(db, ctx, station, radius_km, out):
    units = family_units(db, ctx, station)
    rows = db.query(Substation).filter(Substation.unit_id.in_(units), Substation.active.is_(True),
                                       Substation.id != station.id).all()
    pool = []
    for st in rows:
        if st.lat is None or st.lon is None:
            out['excluded']['tanpa_koordinat'] = out['excluded'].get('tanpa_koordinat', 0) + 1
            continue
        dist = eng.distance_km(float(station.lat), float(station.lon), float(st.lat), float(st.lon))
        if radius_km is None or dist <= radius_km:
            pool.append((st, dist))
    pool.sort(key=lambda item: item[1])
    return pool[:EXAMINE_CAP]


def review(db, ctx, station_id, kind, target_id, line=None, portion=None, measurement_id=None, today=None):
    station = visible_station(db, ctx, station_id)
    assessor, x, ev_x, z, ev_z = load_pair(db, ctx, station, target_id, measurement_id)
    if ev_x['overload'] is None or ev_z['overload'] is None:
        raise HTTPException(422, 'Beban salah satu gardu tidak dapat dinilai (arus belum lengkap)')
    out = {'kind': kind, 'disclaimer': DISCLAIMER, 'target': target_info(z, ev_z, today),
           'source': target_info(x, ev_x, today)}
    if kind == 'swap':
        if x['phase'] != z['phase']:
            raise HTTPException(422, 'Trafo hanya dapat ditukar antar gardu dengan fase sama')
        out['sides'] = eng.review_swap(assessor.evaluate, x, z)
        out['option'] = eng.swap_option(assessor.evaluate, x, z)
    elif kind == 'move':
        if line not in eng.movable_lines(x):
            raise HTTPException(422, 'Jurusan tidak dapat dipindah (arus kosong atau nol)')
        if not isinstance(portion, int) or not 1 <= portion <= 100:
            raise HTTPException(422, 'Porsi harus bilangan bulat 1 sampai 100 persen')
        if eng.target_line(z) is None:
            raise HTTPException(422, 'Arus gardu tujuan tidak lengkap')
        out.update(line_no=line, portion=portion, sides=eng.review_move(assessor.evaluate, x, z, line, portion),
                   option=eng.move_option(assessor.evaluate, x, z, line))
    else:
        raise HTTPException(422, 'Jenis harus swap atau move')
    after = [s['after'] for s in out['sides']]
    out['ok_after'] = all(eng.is_ok(a) for a in after)
    return out
