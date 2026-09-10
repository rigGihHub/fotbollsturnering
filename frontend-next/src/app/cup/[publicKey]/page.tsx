import { getCup, getStandings } from "@/lib/api";
import { PublicCupView } from "@/components/PublicCupView";

export default async function CupPage({ params }: { params: Promise<{publicKey:string}> }) {
  const { publicKey } = await params;
  const [cup, standings] = await Promise.all([getCup(publicKey), getStandings(publicKey)]);
  return <PublicCupView cup={cup} standings={standings.groups || []} />;
}
