export type Tournament = {
  id: number; name: string; public_slug?: string | null; sport?: string | null;
  start_date?: string | null; end_date?: string | null; organizer?: string | null;
  arena_address?: string | null; public_information?: string | null;
};
export type Team = { id:number; name:string; group_id?:number|null; age_class?:string|null; primary_color?:string|null; secondary_color?:string|null };
export type Match = { id:number; stage?:string|null; group_id?:number|null; scheduled_start?:string|null; pitch_number?:string|number|null; home_source?:string|null; away_source?:string|null; home_score?:number|null; away_score?:number|null };
export type Group = { id:number; name:string; age_class?:string|null };
export type Bracket = { id:number; name:string; matches?:Match[] };
export type VenuePoint = {id:number;kind?:string;label?:string;detail?:string;url?:string};
export type CupSnapshot = { tournament:Tournament; teams:Team[]; groups:Group[]; matches:Match[]; brackets:Bracket[]; venue_points:VenuePoint[] };
export type StandingRow = { position:number; team_id:number; Lag:string; S:number; V:number; O:number; F:number; MS:string|number; P:number };
export type TeamSummary = { team_id:number; matches:number; played:number; next_match?:Match|null; latest_result?:Match|null; group_position?:number|null; next_playoff_match?:Match|null };
export type TeamSummaryPayload = { team:Team; summary:TeamSummary; notifications?:Array<{id:number;title?:string;message?:string}> };
