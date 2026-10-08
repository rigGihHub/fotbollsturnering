import type { Metadata } from "next";
import { cache } from "react";
import { CupNaviApiError, getCup } from "@/lib/api";
import { cupShareTitle } from "@/lib/cup-share-title";
import { publicCupUrl } from "@/lib/public-site-url";
import { PublicCupView } from "@/components/PublicCupView";
import PublicCupPreview from "@/components/public-cup-preview";
import PublicCupRecovery from "@/components/public-cup-recovery";

export const revalidate=15;
const readCup=cache(getCup);
type Props={params:Promise<{publicKey:string}>;searchParams:Promise<{preview?:string;cup?:string;from?:string}>};

export async function generateMetadata({params,searchParams}:Props):Promise<Metadata> {
  const [{publicKey},query]=await Promise.all([params,searchParams]);
  if(query.preview==="1"&&Number(query.cup)>0){
    // Only the public endpoint may supply names to link-preview crawlers.
    return {title:"CupNavi - Förhandsgranskning",robots:{index:false,follow:false}};
  }
  try {
    const cup=await readCup(publicKey);
    const title=cupShareTitle(cup.tournament.name);
    const description=`Följ ${cup.tournament.name}: spelschema, tabeller och resultat.`;
    const url=publicCupUrl(`/cup/${encodeURIComponent(publicKey)}`);
    return {
      title,description,
      alternates:{canonical:url},
      openGraph:{title,description,url,siteName:"CupNavi",type:"website",locale:"sv_SE"},
      twitter:{card:"summary",title,description},
    };
  } catch {
    // Preserve the existing recovery flow when the public API is unavailable.
    return {title:"CupNavi",description:"Matcher, tabeller och resultat i CupNavi."};
  }
}

export default async function CupPage({params,searchParams}:Props){
  const [{publicKey},query]=await Promise.all([params,searchParams]);
  if(query.preview==="1"&&Number(query.cup)>0)return <PublicCupPreview publicKey={publicKey} cupId={Number(query.cup)}/>;
  try {
    const cup=await readCup(publicKey);
    return <PublicCupView key={publicKey} publicKey={publicKey} initialCup={cup} initialStandings={cup.standings??[]} reporterReturn={query.from==="reporter"}/>;
  } catch(error) {
    if(error instanceof CupNaviApiError&&(error.status===404||error.status===429||error.status>=500)||error instanceof Error&&["TimeoutError","AbortError","TypeError"].includes(error.name)){
      return <PublicCupRecovery publicKey={publicKey} reporterReturn={query.from==="reporter"}/>;
    }
    throw error;
  }
}
