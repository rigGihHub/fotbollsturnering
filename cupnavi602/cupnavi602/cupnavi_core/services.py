"""Application-service contracts that do not import Streamlit.

v139 starts the separation of domain/application logic from the UI. Existing
functions can migrate behind these interfaces incrementally without a rewrite.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any

class TournamentRepository(Protocol):
    def get_tournament(self, tournament_id: int) -> Any: ...
    def list_teams(self, tournament_id: int) -> list[Any]: ...
    def list_matches(self, tournament_id: int) -> list[Any]: ...

@dataclass
class TournamentSnapshot:
    tournament: Any
    teams: list[Any]
    matches: list[Any]

class TournamentQueryService:
    def __init__(self, repository: TournamentRepository):
        self.repository = repository

    def snapshot(self, tournament_id: int) -> TournamentSnapshot:
        return TournamentSnapshot(
            tournament=self.repository.get_tournament(tournament_id),
            teams=self.repository.list_teams(tournament_id),
            matches=self.repository.list_matches(tournament_id),
        )
