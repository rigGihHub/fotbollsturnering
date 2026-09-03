from pathlib import Path
from datetime import datetime
import importlib.util, sys

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
VIEW=(ROOT/'cupnavi_core/schedule_workspace_view.py').read_text(encoding='utf-8')

def _load():
    spec=importlib.util.spec_from_file_location('schedule_improvement_v366',ROOT/'cupnavi_core/schedule_improvement.py')
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod

def test_optimizer_can_improve_short_rest_by_swapping_existing_slots():
    mod=_load()
    matches=[
        {'id':1,'stage':'Gruppspel','scheduled_start':'2026-09-01T09:00:00','pitch_number':1,'referee_id':1,'home_source':'team:1','away_source':'team:2','home_score':None,'away_score':None,'schedule_locked':0},
        {'id':2,'stage':'Gruppspel','scheduled_start':'2026-09-01T09:30:00','pitch_number':2,'referee_id':2,'home_source':'team:1','away_source':'team:3','home_score':None,'away_score':None,'schedule_locked':0},
        {'id':3,'stage':'Gruppspel','scheduled_start':'2026-09-01T10:30:00','pitch_number':1,'referee_id':1,'home_source':'team:4','away_source':'team:5','home_score':None,'away_score':None,'schedule_locked':0},
        {'id':4,'stage':'Gruppspel','scheduled_start':'2026-09-01T11:00:00','pitch_number':2,'referee_id':2,'home_source':'team:2','away_source':'team:3','home_score':None,'away_score':None,'schedule_locked':0},
    ]
    proposal=mod.build_schedule_improvement(matches,match_duration_minutes=20,minimum_rest_minutes=25)
    assert proposal['improved'] is True
    assert proposal['after']['objective'] < proposal['before']['objective']
    assert proposal['after']['overlap'] == 0

def test_optimizer_protects_teams_with_requests():
    mod=_load()
    matches=[
        {'id':1,'stage':'Gruppspel','scheduled_start':'2026-09-01T09:00:00','pitch_number':1,'referee_id':1,'home_source':'team:1','away_source':'team:2','home_score':None,'away_score':None,'schedule_locked':0},
        {'id':2,'stage':'Gruppspel','scheduled_start':'2026-09-01T09:30:00','pitch_number':2,'referee_id':2,'home_source':'team:1','away_source':'team:3','home_score':None,'away_score':None,'schedule_locked':0},
        {'id':3,'stage':'Gruppspel','scheduled_start':'2026-09-01T10:30:00','pitch_number':1,'referee_id':1,'home_source':'team:4','away_source':'team:5','home_score':None,'away_score':None,'schedule_locked':0},
    ]
    proposal=mod.build_schedule_improvement(matches,match_duration_minutes=20,minimum_rest_minutes=25,protected_team_ids={1})
    assert proposal['eligible_count'] == 1
    assert proposal['updates'] == []

def test_ui_is_preview_first_and_explicit_apply():
    assert '✨ Optimera befintligt schema' in VIEW
    assert 'Beräkna förbättring' in VIEW
    assert 'Före → efter' in VIEW
    assert 'Använd det förbättrade schemat' in VIEW
    assert 'Inget ändras förrän du godkänner det.' in VIEW

def test_version():
    assert 'APP_BUILD_VERSION = "2026.09.03-423-PUBLIC-INFO-COLD-START"' in APP
