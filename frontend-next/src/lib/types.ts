export type Tournament = {
  id: number; name: string; public_slug?: string | null; sport?: string | null;
  start_date?: string | null; end_date?: string | null; organizer?: string | null;
  arena_address?: string | null; public_information?: string | null;
  is_published?: number | boolean | null;
  arrangement_type?: "matchcamp"|"tournament"|"tournament_playoffs"|"custom"|null;
  results_counted?: number | boolean | null;
  show_scorer_stats?: number | boolean | null; show_assist_stats?: number | boolean | null;
  show_card_stats?: number | boolean | null; show_fairness?: number | boolean | null;
  show_public_weather?: number | boolean | null; show_public_kits?: number | boolean | null; show_public_away_kits?: number | boolean | null; show_public_logos?: number | boolean | null;
  points_win?:number|null; points_draw?:number|null; points_loss?:number|null; table_tiebreak?:string|null;
  halves?:number|null; minutes_per_half?:number|null; halftime_minutes?:number|null; pitch_break_minutes?:number|null; minimum_team_rest_minutes?:number|null; avoid_consecutive_matches?:number|boolean|null; consecutive_match_break_minutes?:number|null;
};
export type Team = { id:number; name:string; group_id?:number|null; age_class?:string|null; primary_color?:string|null; secondary_color?:string|null; home_pattern?:string|null; home_color_2?:string|null; away_pattern?:string|null; away_color_2?:string|null; logo_url?:string|null; logo_source_url?:string|null };
export type ResolvedParticipant = { source:string; kind:string; resolved:boolean; team_id?:number|null; team_name?:string|null; reason?:string };
export type Match = { id:number; stage?:string|null; group_id?:number|null; scheduled_start?:string|null; pitch_number?:string|number|null; home_source?:string|null; away_source?:string|null; home_score?:number|null; away_score?:number|null; home_penalties?:number|null; away_penalties?:number|null; match_status?:"not_started"|"live"|"halftime"|"finished"|null; status_updated_at?:string|null; actual_started_at?:string|null; actual_finished_at?:string|null; home_participant?:ResolvedParticipant; away_participant?:ResolvedParticipant };
export type Group = { id:number; name:string; age_class?:string|null };
export type Bracket = { id:number; name:string; size?:number|null; qualification_rule?:string|null; source_rule?:string|null; group_positions?:string|null; qualifying_positions?:string|null; matches?:Match[] };
export type VenuePoint = {id:number;kind?:string;label?:string;detail?:string;url?:string};
export type MatchParticipantResolution = { home:ResolvedParticipant; away:ResolvedParticipant };
export type ParticipantResolutionMap = Record<string,MatchParticipantResolution>;
export type Pitch = { pitch_number:number; name:string };
export type CupSnapshot = { tournament:Tournament; teams:Team[]; groups:Group[]; matches:Match[]; brackets:Bracket[]; venue_points:VenuePoint[]; pitches?:Pitch[]; participant_resolution?:ParticipantResolutionMap };
export type StandingRow = { position:number; team_id:number; Lag:string; S:number; V:number; O:number; F:number; MS:string|number; P:number };
export type TeamSummary = { team_id:number; matches:number; played:number; next_match?:Match|null; latest_result?:Match|null; group_position?:number|null; next_playoff_match?:Match|null };
export type TeamSummaryPayload = { team:Team; summary:TeamSummary; notifications?:Array<{id:number;title?:string;message?:string}> };

export type PlayerStatistic = {
  player_id:number; player_name:string; player_number?:number|null;
  team_id:number; team_name:string; goals:number; assists:number; yellow_cards:number; red_cards:number;
};
export type TeamDisciplineStatistic = { team_id:number; team_name:string; yellow_cards:number; red_cards:number };
export type PublicStatistics = {
  enabled:{scorers:boolean;assists:boolean;cards:boolean;fairness:boolean};
  scorers:PlayerStatistic[]; assists:PlayerStatistic[]; cards:PlayerStatistic[]; discipline:TeamDisciplineStatistic[];
};
