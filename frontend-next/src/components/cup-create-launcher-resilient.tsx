"use client";

import CupCreateLauncherV6 from "./cup-create-launcher-v6";

/**
 * This launcher is mounted only inside AdminAuthShell's authenticated branch.
 * Do not perform a second session request here: duplicate auth probes were a
 * source of race conditions on mobile/Render cold starts and could make the
 * + Ny cup control disappear even while the parent session was valid.
 */
export default function CupCreateLauncherResilient({cups}:{cups:Array<{id:number;name:string;public_slug?:string|null;is_published?:boolean|number}>}) {
  return <CupCreateLauncherV6 cups={cups} />;
}
