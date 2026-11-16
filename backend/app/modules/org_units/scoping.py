"""Small, consistent checks for unit-owned saved configuration."""
from fastapi import HTTPException
from ...db import Asset, Metric
from .repository import home_unit


def owned(item, unit_id, title='Konfigurasi'):
    if item is None or item.unit_id != unit_id:
        raise HTTPException(404, f'{title} tidak ditemukan')
    return item


def metric_codes(db, unit_id, active_only=False):
    query = db.query(Metric).filter_by(unit_id=unit_id)
    if active_only:
        query = query.filter(Metric.active.is_(True))
    return {m.code: m for m in query.all()}


def check_metric_codes(db, unit_id, codes):
    available = metric_codes(db, unit_id)
    if not set(codes).issubset(available):
        raise HTTPException(404, 'Parameter di luar unit')
    return available


def check_asset(db, unit_id, asset_id):
    if asset_id is not None and not db.query(Asset.id).filter_by(
            id=asset_id, unit_id=unit_id).first():
        raise HTTPException(404, 'Peralatan di luar unit')


def scoped_owner(db, scope, unit_id):
    """Preserve old unique(scope, owner_id) without changing its constraint.

    Old home row keeps its legacy scope. New unit uses a distinct scope key;
    APIs still speak public 'system'/'user' only.
    """
    if unit_id == home_unit(db).id:
        return scope
    prefix = {'system': 's', 'user': 'u'}[scope]
    return f'{prefix}{unit_id}'
