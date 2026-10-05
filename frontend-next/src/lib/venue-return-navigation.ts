let scheduleReturnCupId: number | null = null;

export function requestScheduleReturn(cupId: number): void {
  scheduleReturnCupId = cupId;
}

export function hasScheduleReturn(cupId: number): boolean {
  return scheduleReturnCupId === cupId;
}

export function consumeScheduleReturn(cupId: number): boolean {
  const shouldReturn = hasScheduleReturn(cupId);
  scheduleReturnCupId = null;
  return shouldReturn;
}
