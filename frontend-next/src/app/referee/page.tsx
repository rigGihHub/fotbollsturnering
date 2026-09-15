import { redirect } from "next/navigation";

export default async function RefereePage({searchParams}:{searchParams:Promise<{cup?:string}>}){
  const query=await searchParams;
  const cup=query.cup?.trim();
  redirect(cup?`/reporter?cup=${encodeURIComponent(cup)}`:"/reporter");
}
