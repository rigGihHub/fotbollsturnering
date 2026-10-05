// Keep the selected files in memory only while moving to the review screen.
let pending: { cupId: number; files: File[] } | null = null;

export function preparePdfUpdate(cupId: number, files: File[]) {
  pending = { cupId, files };
}

export function takePdfUpdateFiles(cupId: number): File[] {
  if (pending?.cupId !== cupId) return [];
  const files = pending.files;
  pending = null;
  return files;
}
