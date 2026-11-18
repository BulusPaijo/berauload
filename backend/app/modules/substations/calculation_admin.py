"""Admin CRUD: code immutability, revisions, deterministic version bump and audit."""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from ...db import now
from .common import audit, dump, require_admin
from .models_calc import (GarduCalcColumn, GarduCalcRule, GarduCalcConstant,
                          GarduCalcSettings, GarduCalcHistory)
from .calculation_rules import (validate_code, inspect_expression,
                                order_columns, validate_rule_shape)

MODELS = {'column': GarduCalcColumn, 'rule': GarduCalcRule,
          'constant': GarduCalcConstant}
FIELDS = {
    'column': {'name','unit','decimals','expression','empty_mode','description',
               'display_order','active'},
    'rule': {'name','kind','group_name','expression','color','marker',
             'display_order','active'},
    'constant': {'name','value','unit','description','active'},
}


def get_config(db):
    return db.get(GarduCalcSettings, 1)


def check_limits(db, kind, data, current=None):
    if kind == 'column':
        if data.get('active', True) and not (current and current.active):
            if db.query(GarduCalcColumn).filter_by(active=True).count() >= 60:
                raise HTTPException(422, 'Maksimal 60 kolom hitung aktif')
    if kind == 'rule' and data.get('active', True):
        if not current or not current.active:
            if db.query(GarduCalcRule).filter_by(active=True).count() >= 40:
                raise HTTPException(422, 'Maksimal 40 aturan aktif')
        if data.get('kind') == 'category':
            group = data.get('group_name', 'Pembebanan')
            groups = {r.group_name for r in db.query(GarduCalcRule).filter_by(
                active=True, kind='category') if not current or r.id != current.id}
            if group not in groups and len(groups) >= 6:
                raise HTTPException(422, 'Maksimal 6 kelompok kategori')


def check_fields(db, kind, data, old=None):
    if not isinstance(data.get('name'), str) or not data['name'].strip() or len(data['name']) > 180:
        raise HTTPException(422, 'Nama wajib 1–180 karakter')
    for key in ('unit', 'group_name', 'description'):
        if key in data and data[key] is not None and (not isinstance(data[key], str) or
                len(data[key]) > (2000 if key == 'description' else 100)):
            raise HTTPException(422, f'{key}: teks di luar batas')
    if 'active' in data and not isinstance(data['active'], bool):
        raise HTTPException(422, 'Status aktif harus benar/salah')
    if 'display_order' in data and (not isinstance(data['display_order'], int) or
            not 0 <= data['display_order'] <= 100000):
        raise HTTPException(422, 'Urutan harus angka bulat 0–100000')
    if kind == 'constant':
        import math
        try: value = float(data['value'])
        except (ValueError, TypeError, KeyError):
            raise HTTPException(422, 'Nilai konstanta wajib angka')
        if not math.isfinite(value) or abs(value) > 1e9:
            raise HTTPException(422, 'Nilai konstanta harus angka berhingga dalam batas')
        if not str(data.get('unit','')).strip():
            raise HTTPException(422, 'Satuan wajib diisi')
    if kind == 'column':
        if not isinstance(data.get('expression'), str):
            raise HTTPException(422, 'Rumus wajib teks')
        if data.get('empty_mode') not in ('batal', 'lewati'):
            raise HTTPException(422, 'saat_kosong harus batal atau lewati')
        if not isinstance(data.get('decimals'), int) or not 0 <= data['decimals'] <= 5:
            raise HTTPException(422, 'Desimal harus 0–5')
        inspect_expression(data['expression'], db)
        order_columns(db, {'kind':'column', **data})
    if kind == 'rule':
        if not isinstance(data.get('expression'), str):
            raise HTTPException(422, 'Syarat wajib teks')
        validate_rule_shape(data.get('kind'), data.get('color'), data.get('marker'))
        if not str(data.get('group_name','')).strip():
            raise HTTPException(422, 'Nama kelompok wajib diisi')
        inspect_expression(data['expression'], db, rule=True)
    check_limits(db, kind, data, old)


def check_references(db, column):
    from .calculation_rules import inspect_expression
    refs = []
    for row in db.query(GarduCalcColumn).filter_by(active=True):
        if row.code != column.code and column.code in inspect_expression(
                row.expression, db)['dependencies']:
            refs.append(row.code)
    for row in db.query(GarduCalcRule).filter_by(active=True):
        if column.code in inspect_expression(row.expression, db, rule=True)['dependencies']:
            refs.append(row.code)
    if refs:
        raise HTTPException(409, 'Tidak boleh arsip; masih dirujuk: '+', '.join(refs))


def persist(db, ctx, kind, data, identity=None):
    require_admin(ctx)
    if kind not in MODELS: raise HTTPException(404, 'Jenis definisi tidak dikenal')
    model = MODELS[kind]
    row = db.get(model, identity) if identity else None
    if identity and row is None: raise HTTPException(404, 'Definisi tidak ditemukan')
    if row:
        if data.get('code', row.code) != row.code:
            raise HTTPException(409, 'Kode permanen tidak dapat diubah')
        before = dump(row)
        complete = {**before, **{k:v for k,v in data.items() if k in FIELDS[kind]}}
    else:
        if 'code' not in data: raise HTTPException(422, 'Kode wajib diisi')
        validate_code(data['code'], db)
        if db.query(model.id).filter_by(code=data['code']).first():
            raise HTTPException(409, 'Kode telah dipakai')
        defaults = {'column': dict(unit='—', decimals=1, empty_mode='batal',
                    display_order=0, active=True, origin='custom'),
                    'rule': dict(kind='finding', group_name='Temuan',
                    color='#607d8b', marker='circle', display_order=0,
                    active=True, origin='custom'),
                    'constant': dict(unit='—',active=True)}
        complete = {**defaults[kind], **{k:v for k,v in data.items()
                    if k in FIELDS[kind] or k == 'code'}}
        before = None
    if row and kind == 'column' and row.active and not complete['active']:
        check_references(db, row)
    if row and kind == 'rule' and complete.get('kind') != row.kind:
        raise HTTPException(409, 'Jenis kategori/temuan permanen')
    if not complete.get('active', True) and not row:
        raise HTTPException(422, 'Definisi baru harus aktif')
    check_fields(db, kind, complete, row)
    if row and all(before.get(key) == complete.get(key) for key in FIELDS[kind]):
        return dump(row)
    if row:
        for key in FIELDS[kind]:
            if key in complete: setattr(row, key, complete[key])
    else:
        row = model(**complete)
        db.add(row)
    db.flush()
    changed = dump(row)
    settings = get_config(db)
    settings.version += 1
    settings.pending = True
    db.add(GarduCalcHistory(kind=kind, code=row.code, version=settings.version,
                             changed_by=ctx.actor.id, before=before, after=changed))
    audit(db, ctx, 'gardu_calc_'+kind+'_save', row.code, before, changed,
          definition_version=settings.version)
    return changed


def restore_default(db, ctx, identity):
    require_admin(ctx)
    row = db.get(GarduCalcColumn, identity)
    if not row: raise HTTPException(404, 'Kolom tidak ditemukan')
    if row.origin != 'default' or not row.default_snapshot:
        raise HTTPException(422, 'Kolom kustom tidak punya bawaan')
    return persist(db, ctx, 'column', row.default_snapshot, row.id)


def update_settings(db, ctx, stale_days):
    require_admin(ctx)
    if not isinstance(stale_days, int) or not 1 <= stale_days <= 3650:
        raise HTTPException(422, 'Hari belum diukur harus 1–3650')
    settings = get_config(db)
    if settings.stale_days != stale_days:
        previous = settings.stale_days
        settings.stale_days = stale_days
        audit(db, ctx, 'gardu_calc_stale_days', 'global',
              {'stale_days': previous}, {'stale_days': stale_days})
    return {'stale_days': settings.stale_days, 'version': settings.version}


def restore_all_defaults(db, ctx):
    """Atomic restore using one definition version and per-column history."""
    require_admin(ctx)
    columns = db.query(GarduCalcColumn).filter_by(origin='default').all()
    changed = []
    for row in columns:
        defaults = row.default_snapshot or {}
        if not defaults: continue
        before = dump(row)
        for field in FIELDS['column']:
            if field in defaults: setattr(row, field, defaults[field])
        if dump(row) != before: changed.append((row, before))
    db.flush()
    order_columns(db)
    if changed:
        settings = get_config(db)
        settings.version += 1
        settings.pending = True
        for row, before in changed:
            after = dump(row)
            db.add(GarduCalcHistory(kind='column', code=row.code,
                version=settings.version, changed_by=ctx.actor.id,
                before=before, after=after))
            audit(db, ctx, 'gardu_calc_column_restore', row.code, before, after,
                  definition_version=settings.version)
    return {'restored': len(changed), 'version': get_config(db).version}


def reorder_rules(db, ctx, kind, codes):
    """One transaction/version for entire group; no half-swapped positions."""
    require_admin(ctx)
    if kind not in ('category','finding') or not isinstance(codes,list):
        raise HTTPException(422,'Jenis atau daftar urutan aturan tidak sah')
    rows=db.query(GarduCalcRule).filter_by(kind=kind,active=True).all()
    indexed={r.code:r for r in rows}
    if len(codes)!=len(indexed) or len(set(codes))!=len(codes) or set(codes)!=set(indexed):
        raise HTTPException(422,'Urutan harus memuat setiap aturan aktif tepat satu kali')
    changed=[]
    for position,code in enumerate(codes):
        row=indexed[code]
        new_order=(position+1)*10
        if row.display_order==new_order:continue
        old=dump(row)
        row.display_order=new_order
        changed.append((row,old))
    if changed:
        version=get_config(db)
        version.version+=1
        version.pending=True
        for row,before in changed:
            after=dump(row)
            db.add(GarduCalcHistory(kind='rule',code=row.code,version=version.version,
                changed_by=ctx.actor.id,before=before,after=after))
            audit(db,ctx,'gardu_calc_rule_reorder',row.code,before,after,
                  definition_version=version.version)
    return {'changed':len(changed),'codes':codes}
