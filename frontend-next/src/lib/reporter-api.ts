import {CLIENT_API_BASE} from "./client-api";

export class ReporterApiError extends Error {
 constructor(message:string,public status:number){super(message);this.name="ReporterApiError"}
}

export async function reporterCall<T>(path:string,token?:string|null,init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers);
 if(token)headers.set("Authorization",`Bearer ${token}`);
 if(init.body)headers.set("Content-Type","application/json");
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
 try{
  const response=await fetch(`${CLIENT_API_BASE}${path}`,{...init,headers,cache:"no-store",signal:controller.signal});
  const payload=await response.json().catch(()=>null);
  if(!response.ok)throw new ReporterApiError(typeof payload?.detail==="string"?payload.detail:`API-fel ${response.status}`,response.status);
  return payload as T;
 }catch(error){
  if(controller.signal.aborted)throw new ReporterApiError("Anslutningen tog för lång tid. Ändringen finns kvar på den här enheten.",408);
  throw error;
 }finally{clearTimeout(timer)}
}
