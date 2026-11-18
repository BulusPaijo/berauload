"""Stage 9d-3 report content: stored 9b results only, empty stays empty."""
from .analysis_data import decorate, summary
from .analysis_queries import filtered, rows as ranked_rows
from .followup_models import GarduFollowup, GarduFollowupType
from .common import child_ids
from .models import Substation, SubstationParam
from .models_calc import GarduCalcRule
from .monitoring_service import stale_days, unmeasured

LIST_LIMIT = 60


def _row(r):
    return [r['code'], r['name'], r['feeder'], r['power_kva'], r['reference'], r['measured_on'],
            ', '.join(f['name'] for f in r['findings'])]


def _list(db, ctx, opt, **change):
    o = opt.model_copy(update={**change, 'sort': 'code', 'desc': False, 'page': 1, 'page_size': LIST_LIMIT})
    from .analysis_queries import reference
    ref = reference(db)
    if ref:
        o = o.model_copy(update={'sort': ref.code, 'desc': True})
    total, chosen = ranked_rows(db, filtered(db, ctx, o), o, LIST_LIMIT)
    return total, [_row(r) for r in decorate(db, chosen)]


def report_data(db, ctx, opt):
    rules = db.query(GarduCalcRule).filter_by(active=True).order_by(GarduCalcRule.display_order).all()
    sums = summary(db, filtered(db, ctx, opt))
    sections = []
    for r in rules:
        if r.kind == 'category':
            total, rows = _list(db, ctx, opt, category=r.code, findings=[])
        else:
            total, rows = _list(db, ctx, opt, category='', findings=[r.code], finding_mode='any')
        if total:
            sections.append({'title': f"{'Kategori' if r.kind == 'category' else 'Temuan'}: {r.name}",
                             'rule': r.expression, 'total': total, 'rows': rows})
    days = stale_days(db)
    late = unmeasured(db, ctx, days, page_size=200)
    types = {t.code: t.name for t in db.query(GarduFollowupType)}
    follow = db.query(GarduFollowup, Substation).join(Substation, Substation.id == GarduFollowup.substation_id)\
        .filter(GarduFollowup.unit_id.in_(child_ids(db, ctx)), GarduFollowup.status.in_(('terbuka', 'dikerjakan')))\
        .order_by(GarduFollowup.due_on.is_(None), GarduFollowup.due_on).limit(300).all()
    return {'summary': sums, 'sections': sections, 'stale_days': days, 'unmeasured': late,
            'followups': [[s.code, s.name, types.get(f.type_code, f.type_code), f.priority, f.status,
                           f.assignee, f.due_on.isoformat() if f.due_on else None, f.note] for f, s in follow],
            'rules': [(r.kind, r.name, r.expression) for r in rules]}


LIST_HEAD = ['Kode', 'Nama', 'Penyulang', 'kVA', 'Nilai acuan', 'Diukur', 'Temuan']
FOLLOW_HEAD = ['Kode', 'Nama', 'Jenis', 'Prioritas', 'Status', 'Penanggung jawab', 'Target', 'Catatan']
LATE_HEAD = ['Kode', 'Nama', 'Penyulang', 'kVA', 'Terakhir diukur', 'Umur (hari)']


def late_rows(data):
    return [[i['code'], i['name'], i['feeder'], i['power_kva'], i['last_measured_on'], i['age_days']]
            for i in data['unmeasured']['items']]


def worksheet_layout(db):
    """Blank field sheet columns per jurusan, grouped by unit with short labels (R S T N)."""
    params = db.query(SubstationParam).filter_by(active=True).order_by(SubstationParam.display_order).all()
    line = [p for p in params if p.scope == 'line']
    station = [p for p in params if p.scope == 'substation']

    def short(group):
        words = [p.name.split() for p in group]
        k = 0
        while len(group) > 1 and all(len(w) > k + 1 and w[k] == words[0][k] for w in words):
            k += 1
        return [' '.join(w[k:]) for w in words]
    groups = []
    for unit in dict.fromkeys(p.unit for p in line):
        g = [p for p in line if p.unit == unit]
        groups.append((unit, short(g), g))
    return groups, [(p.name, p.unit) for p in station]
