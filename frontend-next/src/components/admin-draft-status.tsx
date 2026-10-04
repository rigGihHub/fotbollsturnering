"use client";
export default function AdminDraftStatus({dirty,busy,error}:{dirty:boolean;busy:boolean;error?:string}) {
  return <p className={`admin-save-status${dirty?' is-unsaved':''}`} role="status" aria-live="polite">
    {busy?'Sparar…':error?'Alla ändringar kunde inte sparas. Ditt utkast finns kvar.':dirty?'Osparade ändringar · utkastet finns kvar när du byter steg.':'Inga osparade ändringar.'}
  </p>;
}
