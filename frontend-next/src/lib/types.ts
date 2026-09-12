export type Tournament = {
  id: number; name: string; public_slug?: string | null; sport?: string | null;
  start_date?: string | null; end_date?: string | null; organizer?: string | null;
  arena_address?: string | null; public_information?: string | null;
  show_scorer_stats?: number | boolean | null; show_assist_stats?: number | boolean | null;
  show_card_stats?: number | boolean | null; show_fairness?: number | boolean | null;
};
export type Team = { id:number; name:string; group_id?:number|null; age_class?:string|null; primary_color?:string|null; secondary_color?:string|null };
export type Match = { id:number; stage?:string|null; group_id?:number|null; scheduled_start?:string|null; pitch_number?:string|number|null; home_source?:string|null; away_source?:string|null; home_score?:number|null; away_score?:number|null };
export type Group = { id:number; name:string; age_class?:string|null };
export type Bracket = { id:number; name:string; matches?:Match[] };
export type VenuePoint = {id:number;kind?:string;label?:string;detail?:string;url?:string};
export type ResolvedParticipant = { source:string; kind:string; resolved:boolean; team_id?:number|null; team_name?:string|null; reason?:string };
export type MatchParticipantResolution = { home:ResolvedParticipant; away:ResolvedParticipant };
export type ParticipantResolutionMap = Record<string,MatchParticipantResolution>;
export type CupSnapshot = { tournament:Tournament; teams:Team[]; groups:Group[]; matches:Match[]; brackets:Bracket[]; venue_points:VenuePoint[]; participant_resolution?:ParticipantResolutionMap };
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
