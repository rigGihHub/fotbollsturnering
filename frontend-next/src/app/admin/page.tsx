import AdminWorkspace from "@/components/admin-workspace";
import AdminOperations from "@/components/admin-operations";
import CupCreateLauncher from "@/components/cup-create-launcher-v5";
import CupSetupGuide from "@/components/cup-setup-guide";
import ApiWakeGuard from "@/components/api-wake-guard";
import PlayoffImportReview from "@/components/playoff-import-review";
import PitchWindowImportReview from "@/components/pitch-window-import-review";
import ImportCompletionSummary from "@/components/import-completion-summary";
import ImportRecoveryGuard from "@/components/import-recovery-guard";

export default function AdminPage(){
  return <><ApiWakeGuard/><ImportRecoveryGuard/><CupCreateLauncher/><CupSetupGuide/><PitchWindowImportReview/><PlayoffImportReview/><ImportCompletionSummary/><AdminWorkspace/><AdminOperations/></>;
}
