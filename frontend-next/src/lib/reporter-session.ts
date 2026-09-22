// Used only to close an expired UI, including offline. The API verifies signatures.
export function reporterSessionDeadline(token:string):number {
  try {
    const encoded=token.split(".")[0].replace(/-/g,"+").replace(/_/g,"/");
    const payload=JSON.parse(atob(encoded.padEnd(Math.ceil(encoded.length/4)*4,"=")));
    const expiry=Number(payload.exp)*1000;
    const revision=String(payload.rev||"");
    const created=Date.parse(/[zZ]$|[+-]\d\d:\d\d$/.test(revision)?revision:`${revision}Z`);
    return Number.isFinite(expiry)&&Number.isFinite(created)?Math.min(expiry,created+72*60*60*1000):0;
  } catch { return 0; }
}
