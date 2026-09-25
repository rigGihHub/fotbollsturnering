from fastapi import Header,HTTPException
from pydantic import BaseModel
from .publish_reporting_repository import admin_publication,set_publication,admin_reporting,reset_result,save_result
from .match_events_admin_repository import admin_event_matches,admin_match_events,update_player_match_events
from .result_correction_repository import playoff_result_correction_impact

class PublicationWrite(BaseModel): published:bool
class ResultWrite(BaseModel):
    home_score:int
    away_score:int
    home_penalties:int|None=None
    away_penalties:int|None=None
    expected_home_score:int|None=None
    expected_away_score:int|None=None
    expected_home_penalties:int|None=None
    expected_away_penalties:int|None=None
class ResultReset(BaseModel):
    expected_home_score:int
    expected_away_score:int
    expected_home_penalties:int|None=None
    expected_away_penalties:int|None=None
    expected_status:str
class EventCounters(BaseModel):
    goals:int=0
    assists:int=0
    yellow_cards:int=0
    red_cards:int=0
class PlayerEventWrite(BaseModel):
    goals:int=0
    assists:int=0
    yellow_cards:int=0
    red_cards:int=0
    expected:EventCounters

def _model_values(model):
    dump=getattr(model,'model_dump',None)
    return dump() if callable(dump) else model.dict()

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
    @app.post('/api/admin/cups/{tournament_id}/reporting/matches/{match_id}/impact')
    def post_result_impact(tournament_id:int,match_id:int,payload:ResultWrite,authorization:str|None=Header(default=None)):
        a=admin_identity(authorization)
        try:r=playoff_result_correction_impact(int(a['id']),tournament_id,match_id,_model_values(payload))
        except ValueError as e:raise HTTPException(422,str(e)) from e
        if r is None:raise HTTPException(404,'Match saknas eller åtkomst nekas')
        return r
    @app.put('/api/admin/cups/{tournament_id}/reporting/matches/{match_id}')
    def put_result(tournament_id:int,match_id:int,payload:ResultWrite,authorization:str|None=Header(default=None)):
        a=admin_identity(authorization)
        try:
            r=save_result(
                int(a['id']),tournament_id,match_id,payload.home_score,payload.away_score,
                payload.expected_home_score,payload.expected_away_score,
                home_penalties=payload.home_penalties,
                away_penalties=payload.away_penalties,
                expected_home_penalties=payload.expected_home_penalties,
                expected_away_penalties=payload.expected_away_penalties,
            )
        except ValueError as e:raise HTTPException(422,str(e)) from e
        except RuntimeError as e:raise HTTPException(409,str(e)) from e
        if r is None:raise HTTPException(404,'Match saknas eller åtkomst nekas')
        return r

    @app.post('/api/admin/cups/{tournament_id}/reporting/matches/{match_id}/reset')
    def post_result_reset(tournament_id:int,match_id:int,payload:ResultReset,authorization:str|None=Header(default=None)):
        a=admin_identity(authorization)
        try:
            r=reset_result(
                int(a['id']),tournament_id,match_id,
                payload.expected_home_score,payload.expected_away_score,
                expected_home_penalties=payload.expected_home_penalties,
                expected_away_penalties=payload.expected_away_penalties,
                expected_status=payload.expected_status,
            )
        except ValueError as e:raise HTTPException(422,str(e)) from e
        except RuntimeError as e:raise HTTPException(409,str(e)) from e
        if r is None:raise HTTPException(404,'Match saknas eller åtkomst nekas')
        return r

    @app.get('/api/admin/cups/{tournament_id}/reporting/events')
    def get_event_matches(tournament_id:int,authorization:str|None=Header(default=None)):
        a=admin_identity(authorization);r=admin_event_matches(int(a['id']),tournament_id)
        if r is None:raise HTTPException(404,'Cup not found or access denied')
        return r

    @app.get('/api/admin/cups/{tournament_id}/reporting/matches/{match_id}/events')
    def get_match_events(tournament_id:int,match_id:int,authorization:str|None=Header(default=None)):
        a=admin_identity(authorization)
        try:r=admin_match_events(int(a['id']),tournament_id,match_id)
        except ValueError as e:raise HTTPException(422,str(e)) from e
        if r is None:raise HTTPException(404,'Match saknas, deltagare är inte avgjorda eller åtkomst nekas')
        return r

    @app.put('/api/admin/cups/{tournament_id}/reporting/matches/{match_id}/events/{player_id}')
    def put_match_event(tournament_id:int,match_id:int,player_id:int,payload:PlayerEventWrite,authorization:str|None=Header(default=None)):
        a=admin_identity(authorization)
        try:r=update_player_match_events(int(a['id']),tournament_id,match_id,player_id,_model_values(payload))
        except ValueError as e:raise HTTPException(422,str(e)) from e
        except RuntimeError as e:raise HTTPException(409,str(e)) from e
        if r is None:raise HTTPException(404,'Match eller spelare saknas eller åtkomst nekas')
