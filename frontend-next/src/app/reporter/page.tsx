import ApiWakeGuard from "@/components/api-wake-guard";
import ReporterClient from "@/components/reporter-client";

export default function ReporterPage(){
  return <><ApiWakeGuard/><ReporterClient/></>;
}
