export type PitchNameMap = Record<string, string>;

/**
 * One display rule for every CupNavi schedule surface.
 * A custom organizer name wins; otherwise the stable Plan X fallback is used.
 */
export function pitchLabel(
  pitchNumber: number | null | undefined,
  pitchNames?: PitchNameMap | null,
): string {
  if (pitchNumber == null) return "Saknas";
  const custom = pitchNames?.[String(pitchNumber)]?.trim();
  return custom || `Plan ${pitchNumber}`;
}
