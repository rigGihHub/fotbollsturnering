export type SchedulePitchRequirement = {
  pitch_number: number;
  play_date: string;
  first_start: string;
  last_end: string;
  match_count: number;
};

export type PitchWindowReadiness = {
  ready: boolean;
  issues: Array<{
    type: "unconfirmed" | "outside_window" | "missing_pitch" | "invalid_schedule";
    message: string;
    pitch_number?: number;
    play_date?: string;
    match_ids: number[];
  }>;
  requirements: SchedulePitchRequirement[];
};

// These are local cup times. Do not convert them to the device's time zone.
export function requiredPitchHours(requirement: SchedulePitchRequirement): string {
  const first = requirement.first_start.slice(11, 16);
  const last = requirement.last_end.slice(11, 16);
  const endDate = requirement.last_end.slice(0, 10);
  return `${first}–${endDate === requirement.play_date ? last : `${endDate} ${last}`}`;
}
