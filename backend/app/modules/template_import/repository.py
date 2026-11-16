"""Read-only catalog and per-unit hourly state, shared by validation and commit."""
from collections import defaultdict
from sqlalchemy import select
from ...db import Metric, Reading, HourRecord, ImportBatch
from ..org_units.models import UnitDayState
from ..input_forms.models import InputFormTab, InputFormPlacement
from ..input_forms.service import fallback_tab, LEGACY_HIDDEN


def eligible_tabs(db, unit_id: int):
    """Return active visible input metrics in the configured tab/column order."""
    tabs = db.query(InputFormTab).filter_by(active=True, unit_id=unit_id).order_by(
        InputFormTab.display_order, InputFormTab.id).all()
    placements = {p.metric_code: p for p in db.query(InputFormPlacement).filter_by(unit_id=unit_id).all()}
    metrics = db.query(Metric).filter_by(unit_id=unit_id, active=True,
                                       input_mode='input').all()
    known = {t.code: [] for t in tabs}
    for metric in metrics:
        if metric.code in LEGACY_HIDDEN:
            continue
        placement = placements.get(metric.code)
        tab = placement.tab_code if placement else fallback_tab(metric, set(known))
        visible = placement.visible if placement else True
        if visible and tab in known:
            order = placement.display_order if placement else metric.display_order
            known[tab].append((order, metric))
    return [(tab, [m for _, m in sorted(known[tab.code],
                                      key=lambda pair: (pair[0], pair[1].code))])
            for tab in tabs if known[tab.code]]


def existing_values(db, unit_id: int, start, end):
    """One global HourRecord, but readings belong to the selected metric unit."""
    rows = (db.query(HourRecord.day, HourRecord.hour, Metric.code, Reading.value)
            .join(Reading, Reading.hour_id == HourRecord.id)
            .join(Metric, Metric.id == Reading.metric_id)
            .filter(Metric.unit_id == unit_id, HourRecord.day >= start,
                    HourRecord.day <= end).all())
    result = defaultdict(dict)
    for day, hour, code, value in rows:
        result[(day, hour)][code] = value
    return result


def statuses(db, unit_id, start, end):
    return {r.day: r.status for r in db.query(UnitDayState).filter(
        UnitDayState.unit_id == unit_id, UnitDayState.day >= start,
        UnitDayState.day <= end).all()}


def imported_already(db, unit_id, sha256):
    return db.query(ImportBatch.id).filter_by(unit_id=unit_id, sha256=sha256).first() is not None
