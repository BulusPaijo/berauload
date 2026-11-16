"""Read-only dependency inventory before a parameter can be deactivated."""
import re
from sqlalchemy.orm import Session
from ...db import Metric
from ..dashboard_builder.models import DashboardLayout
from ..topology.models import TopologyDiagram
from ..formulas.models import FormulaDefinition
from ..historical.models import HistoricalDefinition
from ..engineering.models import EngineeringRule
from ..report_builder.models import ReportTemplate
from ..data_export.models import ExportTemplate
from ..input_forms.models import InputFormPlacement
from ..dashboard_settings.models import DashboardChartSettings
from ..standard_reports.models import StandardReportSelection


def _codes_in(value, code):
    if isinstance(value, list):
        return any(_codes_in(x, code) for x in value)
    if isinstance(value, dict):
        return any(_codes_in(x, code) for x in value.values())
    return isinstance(value, str) and value == code


def _expression_uses(expression: str, code: str) -> bool:
    return bool(re.search(r'(?<![a-zA-Z0-9_])' + re.escape(code) +
                          r'(?![a-zA-Z0-9_])', expression or ''))


def metric_usage(db: Session, metric: Metric) -> list[dict]:
    """Only live references; historical snapshots are not modified or deleted."""
    code, used = metric.code, []
    groups = [
        ('dashboard', db.query(DashboardLayout).filter_by(archived=False).all(), 'panels'),
        ('topologi', db.query(TopologyDiagram).filter_by(archived=False).all(), 'layout'),
        ('template_laporan', db.query(ReportTemplate).filter_by(archived=False).all(), 'blocks'),
        ('template_export', db.query(ExportTemplate).filter_by(archived=False).all(), 'spec'),
        ('grafik_pengaturan', db.query(DashboardChartSettings).all(), 'metric_codes'),
    ]
    for category, rows, field in groups:
        for row in rows:
            if _codes_in(getattr(row, field), code):
                used.append({'category': category, 'id': row.id, 'name': getattr(row, 'name', category)})
    for category, cls in [('formula', FormulaDefinition),
                          ('perhitungan_historis', HistoricalDefinition),
                          ('engineering_rule', EngineeringRule)]:
        query = db.query(cls)
        if hasattr(cls, 'archived'):
            query = query.filter_by(archived=False)
        if hasattr(cls, 'status'):
            query = query.filter(cls.status != 'archived')
        for row in query.all():
            if _expression_uses(row.expression, code):
                used.append({'category': category, 'id': row.id,
                             'name': getattr(row, 'name', f'formula:{row.id}')})
    for row in db.query(StandardReportSelection).filter_by(metric_code=code):
        used.append({'category': 'laporan_standar', 'id': row.id, 'name': row.scope})
    for row in db.query(InputFormPlacement).filter_by(metric_code=code, visible=True):
        used.append({'category': 'form_input', 'id': row.id, 'name': row.tab_code})
    if metric.role_key:
        used.append({'category': 'parameter_utama', 'id': metric.id, 'name': metric.role_key})
    return used
