from fastapi import Header,HTTPException
from pydantic import BaseModel
from .publish_reporting_repository import admin_publication,set_publication,admin_reporting,save_result
class PublicationWrite(BaseModel): published:bool
class ResultWrite(BaseModel):
    home_score:int;away_score:int;expected_home_score:int|None=None;expected_away_score:int|None=None
def register_publish_reporting_routes(app,admin_identity):
    @app.get('/api/admin/cups/{tournament_id}/publication')
    def get_publication(tournament_id:int,authorization:str|None=Header(default=None)):
        a=admin_identity(authorization);r=admin_publication(int(a['id']),tournament_id)
        if r is None:raise HTTPException(404,'Cup not found or access denied')
        return r
    @app.put('/api/admin/cups/{tournament_id}/publication')
    def put_publication(tournament_id:int,payload:PublicationWrite,authorization:str|None=Header(default=None)):
        a=admin_identity(authorization)
        try:r=set_publication(int(a['id']),tournament_id,payload.published)
        except ValueError as e:raise HTTPException(409,str(e)) from e
        if r is None:raise HTTPException(404,'Cup not found or access denied')
        return r
    @app.get('/api/admin/cups/{tournament_id}/reporting')
    def get_reporting(tournament_id:int,authorization:str|None=Header(default=None)):
        a=admin_identity(authorization);r=admin_reporting(int(a['id']),tournament_id)
        if r is None:raise HTTPException(404,'Cup not found or access denied')
        return r
    @app.put('/api/admin/cups/{tournament_id}/reporting/matches/{match_id}')
    def put_result(tournament_id:int,match_id:int,payload:ResultWrite,authorization:str|None=Header(default=None)):
        a=admin_identity(authorization)
        try:r=save_result(int(a['id']),tournament_id,match_id,payload.home_score,payload.away_score,payload.expected_home_score,payload.expected_away_score)
        except ValueError as e:raise HTTPException(422,str(e)) from e
        except RuntimeError as e:raise HTTPException(409,str(e)) from e
        if r is None:raise HTTPException(404,'Match saknas eller åtkomst nekas')
        return r
