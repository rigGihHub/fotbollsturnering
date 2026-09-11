"""FastAPI route registration for referee, playoff, publication, reporting, exports and import."""
from __future__ import annotations
from fastapi import Header,HTTPException
from pydantic import BaseModel
from .playoff_admin_repository import admin_playoffs,update_playoff_settings
from .referee_admin_repository import admin_referees,assign_referee,create_referee,delete_referee,update_referee
from .publish_reporting_routes import register_publish_reporting_routes
from .export_routes import register_export_routes
from .import_routes import register_import_routes
class RefereeWrite(BaseModel):
 name:str|None=None;email:str|None=None;phone:str|None=None;notes:str|None=None;active:bool|None=None
class RefereeAssignmentWrite(BaseModel):referee_id:int|None=None
class PlayoffSettingsWrite(BaseModel):
 playoff_format:str|None=None;bronze_match:bool|None=None;playoff_tie_rule:str|None=None;playoff_extra_time_minutes:int|None=None
def _model_values(model):
 d=getattr(model,'model_dump',None);return d(exclude_unset=True) if callable(d) else model.dict(exclude_unset=True)
def register_competition_admin_routes(app,admin_identity):
 @app.get('/api/admin/cups/{tournament_id}/referees')
 def get_referees(tournament_id:int,authorization:str|None=Header(default=None)):
  a=admin_identity(authorization);r=admin_referees(int(a['id']),tournament_id)
  if r is None:raise HTTPException(404,'Cup not found or access denied')
  return r
 @app.post('/api/admin/cups/{tournament_id}/referees',status_code=201)
 def post_referee(tournament_id:int,payload:RefereeWrite,authorization:str|None=Header(default=None)):
  a=admin_identity(authorization)
  try:r=create_referee(int(a['id']),tournament_id,_model_values(payload))
  except ValueError as e:raise HTTPException(422,str(e)) from e
  if r is None:raise HTTPException(404,'Cup not found or access denied')
  return r
 @app.put('/api/admin/cups/{tournament_id}/referees/{referee_id}')
 def put_referee(tournament_id:int,referee_id:int,payload:RefereeWrite,authorization:str|None=Header(default=None)):
  a=admin_identity(authorization)
  try:r=update_referee(int(a['id']),tournament_id,referee_id,_model_values(payload))
  except ValueError as e:raise HTTPException(422,str(e)) from e
  if r is None:raise HTTPException(404,'Domare saknas eller åtkomst nekas')
  return r
 @app.delete('/api/admin/cups/{tournament_id}/referees/{referee_id}')
 def remove_referee(tournament_id:int,referee_id:int,authorization:str|None=Header(default=None)):
  a=admin_identity(authorization)
  try:r=delete_referee(int(a['id']),tournament_id,referee_id)
  except ValueError as e:raise HTTPException(409,str(e)) from e
  if r is None:raise HTTPException(404,'Domare saknas eller åtkomst nekas')
  return {'deleted':True,'referee':r}
 @app.put('/api/admin/cups/{tournament_id}/referees/matches/{match_id}')
 def put_assignment(tournament_id:int,match_id:int,payload:RefereeAssignmentWrite,authorization:str|None=Header(default=None)):
  a=admin_identity(authorization)
  try:r=assign_referee(int(a['id']),tournament_id,match_id,payload.referee_id)
  except ValueError as e:raise HTTPException(422,str(e)) from e
  if r is None:raise HTTPException(404,'Match saknas eller åtkomst nekas')
  return r
 @app.get('/api/admin/cups/{tournament_id}/playoffs')
 def get_playoffs(tournament_id:int,authorization:str|None=Header(default=None)):
  a=admin_identity(authorization);r=admin_playoffs(int(a['id']),tournament_id)
  if r is None:raise HTTPException(404,'Cup not found or access denied')
  return r
 @app.put('/api/admin/cups/{tournament_id}/playoffs')
 def put_playoffs(tournament_id:int,payload:PlayoffSettingsWrite,authorization:str|None=Header(default=None)):
  a=admin_identity(authorization)
  try:r=update_playoff_settings(int(a['id']),tournament_id,_model_values(payload))
  except ValueError as e:raise HTTPException(422,str(e)) from e
  if r is None:raise HTTPException(404,'Cup not found or access denied')
  return r
 register_publish_reporting_routes(app,admin_identity)
 register_export_routes(app,admin_identity)
 register_import_routes(app,admin_identity)
