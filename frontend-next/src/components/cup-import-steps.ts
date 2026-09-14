export const CUP_IMPORT_STEPS = [
  { id: 0, label: "Cup" },
  { id: 1, label: "Lag" },
  { id: 2, label: "Matcher" },
  { id: 4, label: "Kontroll" },
] as const;

export const CUP_IMPORT_STEP_IDS = CUP_IMPORT_STEPS.map(step => step.id);

export function nextCupImportStep(current:number) {
  const index = CUP_IMPORT_STEP_IDS.indexOf(current as 0|1|2|4);
  return CUP_IMPORT_STEP_IDS[Math.min(CUP_IMPORT_STEP_IDS.length - 1, Math.max(0, index + 1))];
}

export function previousCupImportStep(current:number) {
  const index = CUP_IMPORT_STEP_IDS.indexOf(current as 0|1|2|4);
  return CUP_IMPORT_STEP_IDS[Math.max(0, index - 1)];
}
