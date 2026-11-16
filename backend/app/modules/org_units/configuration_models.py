"""Registered configuration owners; revision tables refer to parent owners."""
from ..input_forms.models import InputFormTab, InputFormPlacement, InputFormRevision
from ..dashboard_builder.models import DashboardLayout
from ..dashboard_settings.models import DashboardChartSettings
from ..topology.models import TopologyDiagram
from ..report_builder.models import ReportTemplate
from ..data_export.models import ExportTemplate
from ..standard_reports.models import StandardReportSelection
from ..formulas.models import FormulaDefinition
from ..historical.models import HistoricalDefinition
from ..engineering.models import EngineeringRule

OWNERS = (InputFormTab, InputFormPlacement, InputFormRevision, DashboardLayout,
          DashboardChartSettings, TopologyDiagram, ReportTemplate, ExportTemplate,
          StandardReportSelection, FormulaDefinition, HistoricalDefinition,
          EngineeringRule)
