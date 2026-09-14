import { getCup, getStandings } from "@/lib/api";
import { PublicCupView } from "@/components/PublicCupView";
import PublicCupPreview from "@/components/public-cup-preview";
export default async function CupPage({params,searchParams}:{params:Promise<{publicKey:string}>;searchParams:Promise<{preview?:string;cup?:string}>}){const {publicKey}=await params;const query=await searchParams;if(query.preview==="1"&&Number(query.cup)>0)return <PublicCupPreview publicKey={publicKey} cupId={Number(query.cup)}/>;const [cup,standings]=await Promise.all([getCup(publicKey),getStandings(publicKey)]);return <PublicCupView publicKey={publicKey} initialCup={cup} initialStandings={standings.groups||[]}/>;}
