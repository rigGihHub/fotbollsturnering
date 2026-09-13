import AdminWorkspace from "@/components/admin-workspace";
import AdminOperations from "@/components/admin-operations";
import CupCreateLauncher from "@/components/cup-create-launcher";
import ApiWakeGuard from "@/components/api-wake-guard";

export default function AdminPage(){
  return <><ApiWakeGuard/><CupCreateLauncher/><AdminWorkspace/><AdminOperations/></>;
}
