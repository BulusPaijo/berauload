from __future__ import annotations
import os, uuid, calendar, hashlib, io, json
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Depends, Request, Response, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from .db import (Base, engine, SessionLocal, get_db, User, LoginSession,
                 Asset, Metric, HourRecord, Reading, DayState, AuditLog, ImportBatch)
from .catalog import ASSETS, METRICS, CODE_MAP, calculate
from .importer import parse_load_excel, MAX_FILE_BYTES
from .security import (hash_password, password_ok, rate_limit, new_session, resolve_session,
                       current_user, require, COOKIE_NAME, SECURE_COOKIE, clear_attempts, cleanup_sessions, set_session_cookie)
from .modules.substations.router import router as substations_router
from .modules.substations.analysis_router import router as substations_analysis_router
from .modules.substations.map_migrations import run as run_substations_map_migration
from .modules.substations.map_router import router as substations_map_router
from .modules.substations.export_migrations import run as run_substations_export_migration
from .modules.substations.export_router import router as substations_export_router
from .modules.substations.followup_migrations import run as run_substations_followup_migration
from .modules.substations.followup_router import router as substations_followup_router
from .modules.substations.end_voltage_migration import run as run_substations_end_voltage_migration
from .modules.substations.monitoring_router import router as substations_monitoring_router
from .modules.substations.analysis_migrations import run as run_substations_analysis_migration
from .modules.substations.calculation_router import router as substations_calc_router
from .modules.substations.calculation_migrations import run as run_substations_calc_migration
from .modules.substations.migrations import run as run_substations_migration
from .modules.branding.router import router as branding_router
from .modules.branding.migrations import run as run_branding_migration
from .modules.sessions.migrations import run as run_session_migration
from .modules.sessions.models import LoginAttempt
from .modules.completeness.router import router as completeness_router
from .modules.formulas.router import router as formula_router
from .modules.formulas.models import FormulaDefinition, SchemaMigration
from .modules.formulas.migrations import run as run_migrations
from .modules.formulas.service import calculate_custom, active_plan
from .modules.monitoring.router import router as monitoring_router
from .modules.dashboard_settings.router import router as chart_settings_router
from .modules.dashboard_settings.models import DashboardChartSettings
from .modules.dashboard_settings.migrations import run as run_chart_migration
from .modules.historical.router import router as historical_router
from .modules.historical.models import HistoricalDefinition, HistoricalRevision
from .modules.historical.migrations import run as run_historical_revision_migration
from .modules.engineering.router import router as engineering_router
from .modules.engineering.models import EngineeringRule, EngineeringRuleRevision
from .modules.engineering.migrations import run as run_engineering_migration
from .modules.dashboard_builder.router import router as builder_router
from .modules.dashboard_builder.migrations import run as run_builder_migration, run_management as run_dashboard_management
from .modules.equipment_kinds.router import router as kinds_router
from .modules.equipment_kinds.models import EquipmentKind
from .modules.equipment_kinds.migrations import run as run_kinds_migration
from .modules.equipment_kinds.repository import by_code as kind_by_code
from .modules.equipment_kinds.service import require_active_kind
from .modules.input_forms.router import router as input_form_router
from .modules.input_forms.migrations import run as run_input_form_migration
from .modules.input_forms.models import InputFormTab, InputFormPlacement, InputFormRevision
from .modules.units.models import UnitDefinition
from .modules.units.router import router as units_router
from .modules.units.migrations import run as run_units_migration
from .modules.data_export.router import router as export_router
from .modules.data_export.migrations import run as run_export_migration
from .modules.performance.router import router as performance_router
from .modules.performance.cache import clear_reading_cache
from .modules.report_builder.router import router as report_builder_router
from .modules.report_builder.migrations import run as run_report_builder_migration
from .modules.standard_reports.router import router as standard_reports_router
from .modules.standard_reports.migrations import run as run_standard_reports_migration
from .modules.standard_reports.models import StandardReportSelection
from .modules.standard_reports.service import compare_years
from .modules.topology.router import router as topology_router
from .modules.topology.migrations import run as run_topology_migration
from .modules.org_units.models import OrgUnit
from .modules.org_units.migrations import precreate as precreate_org_units, run as run_org_units_migration
from .modules.org_units.migration_home import run as run_org_home_migration
from .modules.org_units.migration_config import ensure_schema as ensure_config_schema, backfill_once as backfill_config_once
from .modules.unit_references.router import router as unit_references_router
from .modules.unit_references.migrations import run as run_unit_references_migration
from .modules.org_units.router import router as org_units_router
from .modules.org_units.copy_router import router as copy_settings_router
from .modules.org_units.repository import (home_unit as org_home, role_conflict,
                                           attach_new_user, mirror_day_state)
from .modules.org_units.service import validate_role_key, OrgError
from .modules.template_import.router import router as template_import_router
from .modules.template_import.migrations import run as run_template_import_migration
from .modules.primary_metrics.router import router as primary_metrics_router
from .modules.records.router import router as records_router, day_status, day_readings
from .modules.analytics_core.router import router as analytics_core_router
from .modules.legacy_reports.router import router as legacy_reports_router
from .modules.parameters.router import router as parameter_router
from .modules.users.router import router as users_router
from .modules.catalog_api.router import router as catalog_scoped_router
from .modules.records.entry import router as records_entry_router
from .modules.legacy_import.router import router as legacy_import_router
from .modules.org_units.context import UnitContext, unit_context

from .modules.org_units.roles import metric_for_role, role_codes, SYSTEM_LOAD, SYSTEM_CAPACITY
from .modules.org_units.usage import metric_usage

@asynccontextmanager
async def app_lifespan(_app):
    setup()
    yield

app=FastAPI(title='BerauLoad',version='1.6.0-stage9d5',docs_url=None,redoc_url=None,lifespan=app_lifespan)
app.include_router(branding_router)
app.include_router(formula_router)
app.include_router(monitoring_router)
app.include_router(substations_router)
app.include_router(substations_analysis_router)
app.include_router(substations_map_router)
app.include_router(substations_export_router)
app.include_router(substations_followup_router)
app.include_router(substations_monitoring_router)
app.include_router(substations_calc_router)
app.include_router(chart_settings_router)
app.include_router(historical_router)
app.include_router(engineering_router)
app.include_router(builder_router)
app.include_router(kinds_router)
app.include_router(input_form_router)
app.include_router(units_router)
app.include_router(export_router)
app.include_router(performance_router)
app.include_router(report_builder_router)
app.include_router(standard_reports_router)
app.include_router(topology_router)
app.include_router(completeness_router)
app.include_router(org_units_router)
app.include_router(unit_references_router)
app.include_router(copy_settings_router)
app.include_router(template_import_router)
app.include_router(primary_metrics_router)
app.include_router(records_router)
app.include_router(analytics_core_router)
app.include_router(legacy_reports_router)
app.include_router(parameter_router)
app.include_router(users_router)
app.include_router(catalog_scoped_router)
app.include_router(records_entry_router)
app.include_router(legacy_import_router)
UPLOAD_DIR=Path(os.getenv('UPLOAD_DIR','/data/uploads'))
STAGING_DIR=UPLOAD_DIR/'staging'
TZ=ZoneInfo('Asia/Makassar')

def audit(db, u, action, target=None, detail=None):
    db.add(AuditLog(user_id=u.id if u else None,action=action,target=target,detail=detail or {}))

def setup():
    precreate_org_units(engine)
    legacy_tables=[t for t in Base.metadata.tables.values()
                   if t.name not in ('formula_definitions','schema_migrations','dashboard_chart_settings','historical_definitions', 'historical_revisions', 'engineering_rules', 'engineering_rule_revisions', 'dashboard_layouts', 'equipment_kinds', 'input_form_tabs', 'input_form_placements', 'input_form_revision', 'unit_definitions', 'export_templates', 'dashboard_revisions', 'dashboard_shares', 'report_templates', 'standard_report_selections', 'topology_diagrams', 'topology_revisions', 'org_units', 'unit_day_states', 'user_unit_access', 'unit_source_changes', 'login_attempts', 'app_branding', 'substation_feeders', 'substation_choices', 'substations', 'substation_master_history', 'substation_params', 'substation_sessions', 'substation_value_flags', 'substation_fields', 'substation_measurements', 'substation_values',
                   'gardu_calc_columns', 'gardu_calc_rules', 'gardu_calc_constants',
                   'gardu_calc_history', 'gardu_calc_settings', 'gardu_calc_values',
                   'gardu_calc_matches', 'gardu_calc_marks',
                   'gardu_analysis_views', 'gardu_analysis_settings', 'gardu_tile_settings',
                   'gardu_export_templates', 'gardu_followup_types', 'gardu_followups',
                   'substation_values_archive')]
    Base.metadata.create_all(bind=engine,tables=legacy_tables)
    ensure_config_schema(engine)
    run_migrations(engine)
    run_session_migration(engine)
    run_branding_migration(engine)
    run_substations_migration(engine)
    run_substations_calc_migration(engine)
    run_substations_analysis_migration(engine)
    run_substations_map_migration(engine)
    run_substations_export_migration(engine)
    run_substations_followup_migration(engine)
    run_substations_end_voltage_migration(engine)
    run_chart_migration(engine)
    run_historical_revision_migration(engine)
    run_engineering_migration(engine)
    run_builder_migration(engine)
    run_dashboard_management(engine)
    run_kinds_migration(engine)
    run_input_form_migration(engine)
    run_units_migration(engine)
    run_export_migration(engine)
    run_report_builder_migration(engine)
    run_standard_reports_migration(engine)
    run_topology_migration(engine)
    run_org_units_migration(engine)
    run_unit_references_migration(engine)
    run_org_home_migration(engine)
    run_template_import_migration(engine)
    backfill_config_once(engine)
    UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    STAGING_DIR.mkdir(parents=True,exist_ok=True)
    with SessionLocal() as db:
        cleanup_sessions(db, force=True)
        home_id = org_home(db).id
        for code,name,kind in ASSETS:
            if not db.query(Asset.id).filter_by(code=code).first():
                db.add(Asset(code=code,name=name,kind=kind,unit_id=home_id))
        db.flush()
        aid={a.code:a.id for a in db.query(Asset).all()}
        for idx,(code,name,unit,group,mode,asset) in enumerate(METRICS):
            if not db.query(Metric.id).filter_by(code=code).first():
                db.add(Metric(code=code,name=name,unit=unit,group_name=group,input_mode=mode,
                              asset_id=aid.get(asset),display_order=idx,unit_id=home_id,
                              role_key={"beban_sistem_kw":"system.load",
                              "daya_pasok_pembangkit_kw":"system.capacity"}.get(code)))
        if not db.query(User.id).first():
            user=os.getenv('ADMIN_USERNAME','admin');pwd=os.getenv('ADMIN_PASSWORD','')
            if len(pwd)<16: raise RuntimeError('ADMIN_PASSWORD wajib minimal 16 karakter di .env')
            new_admin=User(username=user,display_name='Administrator',password_hash=hash_password(pwd),role='admin')
            db.add(new_admin)
            attach_new_user(db,new_admin)
        db.commit()

@app.get('/api/health')
def health(db:Session=Depends(get_db)):
    try:db.execute(text('SELECT 1'))
    except Exception:raise HTTPException(503,'Database tidak dapat dihubungi')
    return {'status':'ok','app':'BerauLoad','version':'1.6.0-stage9d5','test_instance':os.getenv('BERAULOAD_TEST_INSTANCE','false').lower()=='true'}

class LoginBody(BaseModel):
    username:str=Field(min_length=2,max_length=70)
    password:str=Field(min_length=1,max_length=200)

@app.post('/api/auth/login')
def login(body:LoginBody,request:Request,response:Response,db:Session=Depends(get_db)):
    ip=request.client.host if request.client else 'unknown'
    cleanup_sessions(db)
    rate_limit(db,ip,body.username)
    u=db.query(User).filter(User.username==body.username).first()
    if not u or not u.active or not password_ok(body.password,u.password_hash):
        raise HTTPException(401,'Username atau password salah')
    clear_attempts(db,ip,body.username)
    token,csrf,age=new_session(db,u)
    set_session_cookie(response,token,age)
    return {'user':{'id':u.id,'username':u.username,'name':u.display_name,'role':u.role},'csrf':csrf}

@app.get('/api/auth/me')
def me(request:Request,response:Response,db:Session=Depends(get_db)):
    u,s=resolve_session(request,db,response)
    return {'user':{'id':u.id,'username':u.username,'name':u.display_name,'role':u.role},
            'csrf':s.csrf_token,'expires_at':(s.expires_at if s.expires_at.tzinfo else s.expires_at.replace(tzinfo=timezone.utc)).isoformat()}

@app.post('/api/auth/logout')
def logout(response:Response,request:Request,u:User=Depends(current_user),db:Session=Depends(get_db)):
    token=request.cookies.get(COOKIE_NAME,'')
    db.query(LoginSession).filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).delete()
    db.commit();response.delete_cookie(COOKIE_NAME,path='/')
    return {'ok':True}

@app.get('/api/audit')
def audit_log(limit:int=100,ctx:UnitContext=Depends(unit_context('read')),db:Session=Depends(get_db)):
    if not ctx.superadmin:
        ctx.role_for('verifier')
    rows=db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(2000).all()
    if not ctx.superadmin:
        home_id=org_home(db).id
        rows=[r for r in rows if (r.detail or {}).get('unit_id',home_id)==ctx.id]
    rows=rows[:min(max(limit,1),300)]
    return [{'at':r.created_at.isoformat(),'user_id':r.user_id,'action':r.action,'target':r.target,'detail':r.detail} for r in rows]

