"""Map points share Stage 9c filtered relation and 9b stored results."""
from collections import Counter
from math import isfinite
from sqlalchemy import func
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from .analysis_data import summary
from .analysis_queries import reference
from .models import SubstationFeeder
from .models_calc import GarduCalcColumn, GarduCalcMatch, GarduCalcRule, GarduCalcSettings, GarduCalcValue
from .analysis_queries import filtered
from .models import Substation, SubstationMeasurement


def valid_coordinate(lat, lon):
    try:
        a, b = float(lat), float(lon)
        return isfinite(a) and isfinite(b) and -90 <= a <= 90 and -180 <= b <= 180
    except (TypeError, ValueError, OverflowError):
        return False


def matching_stations(db, ctx, opt):
    """One pin per station, even when analysis mode is 'semua'."""
    candidates = filtered(db, ctx, opt).order_by(None).subquery()
    ranked = db.query(candidates.c.sid, candidates.c.mid,
        candidates.c.last_day, candidates.c.feeder_id,
        func.row_number().over(partition_by=candidates.c.sid,
                               order_by=(SubstationMeasurement.measured_on.desc(),
                                         candidates.c.mid.desc())).label('rn'))        .outerjoin(SubstationMeasurement, SubstationMeasurement.id == candidates.c.mid)        .subquery()
    return db.query(ranked.c.sid, ranked.c.mid, ranked.c.last_day,
                    ranked.c.feeder_id).filter(ranked.c.rn == 1).order_by(ranked.c.sid)


CHUNK = 500


def _slim_batch(db, batch, ref, color_col, feeders, rules, settings, today):
    """Compact per-pin rows; heavy detail is lazy-loaded on click (9d-2)."""
    sids = [r.sid for r in batch]
    mids = [r.mid for r in batch if r.mid]
    stations = {s.id: s for s in db.query(Substation).filter(Substation.id.in_(sids))}
    hits = defaultdict(list)
    if mids:
        for mid, rule_id in db.query(GarduCalcMatch.measurement_id, GarduCalcMatch.rule_id).filter(
                GarduCalcMatch.measurement_id.in_(mids)):
            if rule_id in rules:
                hits[mid].append(rules[rule_id])
    values = {}
    wanted = {c.id: c.code for c in (ref, color_col) if c is not None}
    if mids and wanted:
        for mid, cid, val in db.query(GarduCalcValue.measurement_id, GarduCalcValue.column_id,
                GarduCalcValue.value).filter(GarduCalcValue.measurement_id.in_(mids),
                GarduCalcValue.column_id.in_(list(wanted))):
            values[(mid, wanted[cid])] = val
    out = []
    for row in batch:
        st = stations[row.sid]
        found = sorted(hits[row.mid], key=lambda r: (r.display_order, r.id))
        cats = [r for r in found if r.kind == 'category']
        cat = cats[0] if cats else None
        age = (today - row.last_day).days if row.last_day else None
        status = ('belum' if age is None else 'lama' if settings and age > settings.stale_days else 'baru')
        point = {'id': st.id, 'code': st.code, 'name': st.name, 'unit_id': st.unit_id,
                 'power_kva': float(st.power_kva), 'feeder_id': st.feeder_id,
                 'feeder': feeders.get(st.feeder_id), 'measurement_id': row.mid,
                 'age_days': age, 'status': status,
                 'reference': values.get((row.mid, ref.code)) if ref else None,
                 'category': {'code': cat.code if cat else 'tidak_dapat_dinilai'},
                 'categories': [{'code': r.code, 'group_name': r.group_name} for r in cats],
                 'finding_codes': [r.code for r in found if r.kind == 'finding'],
                 'columns': ({color_col.code: {'value': values.get((row.mid, color_col.code))}}
                             if color_col else {}),
                 'lat': st.lat, 'lon': st.lon}
        out.append(point)
    return out


def map_points(db, ctx, opt, color_column=None):
    selection = matching_stations(db, ctx, opt)
    chosen = selection.all()
    ref = reference(db)
    color_col = (db.query(GarduCalcColumn).filter_by(code=color_column, active=True).first()
                 if color_column else None)
    feeders = {f.id: f.name for f in db.query(SubstationFeeder.id, SubstationFeeder.name)}
    rules = {r.id: r for r in db.query(GarduCalcRule).filter_by(active=True)}
    settings = db.get(GarduCalcSettings, 1)
    today = datetime.now(ZoneInfo('Asia/Makassar')).date()
    points, missing, missing_count, flags = [], [], 0, Counter()
    for offset in range(0, len(chosen), CHUNK):
        for row in _slim_batch(db, chosen[offset:offset + CHUNK], ref, color_col,
                               feeders, rules, settings, today):
            if not valid_coordinate(row['lat'], row['lon']):
                missing_count += 1
                if len(missing) < 100:
                    missing.append({'id': row['id'], 'code': row['code'], 'name': row['name']})
                continue
            row['lat'], row['lon'] = round(float(row['lat']), 6), round(float(row['lon']), 6)
            for code in row['finding_codes']:
                flags[code] += 1
            points.append(row)
    return {'points': points, 'total': len(chosen),
            'missing_coordinates': missing_count,
            'missing': missing, 'missing_truncated': missing_count > len(missing),
            'summary': summary(db, filtered(db, ctx, opt)),
            'finding_counts_on_map': dict(flags)}
