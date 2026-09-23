import { CupNaviApiError, getCup } from "@/lib/api";
import { PublicCupView } from "@/components/PublicCupView";
import PublicCupPreview from "@/components/public-cup-preview";
import PublicCupRecovery from "@/components/public-cup-recovery";
import { notFound } from "next/navigation";
export const revalidate=15;
export default async function CupPage({params,searchParams}:{params:Promise<{publicKey:string}>;searchParams:Promise<{preview?:string;cup?:string;from?:string}>}){const {publicKey}=await params;const query=await searchParams;if(query.preview==="1"&&Number(query.cup)>0)return <PublicCupPreview publicKey={publicKey} cupId={Number(query.cup)}/>;try{const cup=await getCup(publicKey);return <PublicCupView publicKey={publicKey} initialCup={cup} initialStandings={[]} reporterReturn={query.from==="reporter"}/>;}catch(error){if(error instanceof CupNaviApiError&&error.status===404)notFound();if(error instanceof CupNaviApiError&&(error.status===429||error.status>=500))return <PublicCupRecovery publicKey={publicKey} reporterReturn={query.from==="reporter"}/>;throw error;}}
