import AdminWorkspace from "@/components/admin-workspace-resilient";
import AdminOperations from "@/components/admin-operations";
import CupCreateLauncher from "@/components/cup-create-launcher-resilient";
import CupSetupGuide from "@/components/cup-setup-guide";
import ApiWakeGuard from "@/components/api-wake-guard";
import AdminRuntimeUx from "@/components/admin-runtime-ux";
import PlayoffImportReview from "@/components/playoff-import-review";
import PitchWindowImportReview from "@/components/pitch-window-import-review";
import ImportCompletionSummary from "@/components/import-completion-summary";
import ImportRecoveryGuard from "@/components/import-recovery-guard";

export default function AdminPage(){
  return <><ApiWakeGuard/><AdminRuntimeUx/><ImportRecoveryGuard/><CupCreateLauncher/><CupSetupGuide/><PitchWindowImportReview/><PlayoffImportReview/><ImportCompletionSummary/><AdminWorkspace/><AdminOperations/></>;
}
