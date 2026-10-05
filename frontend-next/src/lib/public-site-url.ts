// Use the verified custom domain for outgoing links, regardless of where
// an organizer opened the app. Internal navigation remains on its current host.
export const PUBLIC_SITE_ORIGIN = "https://www.cup-navi.com";

export function publicSiteUrl(path:string):string {
  const parsed=new URL(path,PUBLIC_SITE_ORIGIN);
  return new URL(`${parsed.pathname}${parsed.search}${parsed.hash}`,PUBLIC_SITE_ORIGIN).toString();
}

export function publicCupUrl(path:string):string {
  // Preview, admin and session parameters must not be copied into cup sharing
  // or QR codes. The slug in the pathname already identifies the public cup.
  return publicSiteUrl(new URL(path,PUBLIC_SITE_ORIGIN).pathname);
}
