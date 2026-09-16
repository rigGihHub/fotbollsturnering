import { CupNaviApiError, getCup, getStandings } from "@/lib/api";
import { PublicCupView } from "@/components/PublicCupView";
import PublicCupPreview from "@/components/public-cup-preview";
import { notFound } from "next/navigation";
import { unstable_cache } from "next/cache";
const getCachedCup=unstable_cache((publicKey:string)=>getCup(publicKey),["public-cup"],{revalidate:30});
const getCachedStandings=unstable_cache((publicKey:string)=>getStandings(publicKey),["public-standings"],{revalidate:30});
export default async function CupPage({params,searchParams}:{params:Promise<{publicKey:string}>;searchParams:Promise<{preview?:string;cup?:string;from?:string}>}){const {publicKey}=await params;const query=await searchParams;if(query.preview==="1"&&Number(query.cup)>0)return <PublicCupPreview publicKey={publicKey} cupId={Number(query.cup)}/>;try{const [cup,standings]=await Promise.all([getCachedCup(publicKey),getCachedStandings(publicKey)]);return <PublicCupView publicKey={publicKey} initialCup={cup} initialStandings={standings.groups||[]} reporterReturn={query.from==="reporter"}/>;}catch(error){if(error instanceof CupNaviApiError&&error.status===404)notFound();throw error;}}
