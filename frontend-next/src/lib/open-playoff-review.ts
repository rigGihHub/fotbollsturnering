export const OPEN_PLAYOFF_REVIEW_EVENT = "cupnavi:open-playoff-review";
export const PLAYOFF_REVIEW_REQUEST_KEY = "cupnavi_playoff_review_requested";

export function includesPlayoffStep(arrangementType: string, currentStep: string) {
  return currentStep === "playoffs" || !["matchcamp", "tournament"].includes(arrangementType);
}

export function openPlayoffReview(cupId: number) {
  sessionStorage.setItem(PLAYOFF_REVIEW_REQUEST_KEY, String(cupId));
  window.location.hash = "playoffs";
  window.dispatchEvent(new CustomEvent(OPEN_PLAYOFF_REVIEW_EVENT, { detail: cupId }));
}
