import type { ReactNode } from "react";
import { parseAdminStep, type AdminStep } from "../lib/admin-navigation";

const stepIcons: Record<AdminStep, ReactNode> = {
  overview: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
  cupinfo: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/></>,
  teams: <><circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M21 20v-2a6 6 0 0 0-4-5.65"/></>,
  groups: <><rect x="3" y="4" width="7" height="16" rx="2"/><rect x="14" y="4" width="7" height="16" rx="2"/><path d="M6 9h1M6 13h1M6 17h1M17 9h1M17 13h1M17 17h1"/></>,
  venues: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M12 5v14M3 9h3v6H3M21 9h-3v6h3"/><circle cx="12" cy="12" r="3"/></>,
  rules: <><path d="M10 6h11M10 12h11M10 18h11M3 6l1.5 1.5L7 4M3 12l1.5 1.5L7 10M3 18l1.5 1.5L7 16"/></>,
  schedule: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 11h18M7 15h2M15 15h2M7 18h2"/></>,
  playoffs: <><path d="M3 4h5v6H3M3 14h5v6H3M8 7h7v10H8M15 12h6"/></>,
  publish: <><rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v4H9zM8 14l3 3 5-6"/></>,
  partners: <><path d="M3 4h9l9 9-8 8-10-10z"/><circle cx="7.5" cy="8" r="1"/></>,
  access: <><path d="M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/></>,
  referees: <><path d="M5 21V3M5 4h14l-3 4 3 4H5"/></>,
  reporting: <><rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 10h18M12 10v10M7 14h1v3M16 14h1v3M8 3v2M16 3v2"/></>,
  import: <><path d="M12 16V3M7 8l5-5 5 5M4 15v5h16v-5"/></>,
  export: <><path d="M12 3v13M7 11l5 5 5-5M4 15v5h16v-5"/></>,
};

export default function AdminNavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return <a href={href} aria-current={active ? "page" : undefined}>
    <svg className="cn-admin-nav__icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {stepIcons[parseAdminStep(href)]}
    </svg>
    <span className="cn-admin-nav__label">{label}</span>
  </a>;
}
