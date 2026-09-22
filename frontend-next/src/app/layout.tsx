import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./ux-polish.css";
import "./ux-v262.css";
import "./ux-v265.css";
import "./admin-step-flow.css";
import "./ui-system-v2615.css";
import "./mode-switch-v2615.css";
import "./ui-system-v2616.css";
import "./admin-mobile-cohesion-v2628.css";
import "./public-ux-v2624.css";
import "./comic-card-v2634.css";
import "./public-system-v2639.css";
import "./brand-v2641.css";
import "./admin-system-v2638.css";
import "./admin-guide-v2643.css";
import "./beginner-flow-v2645.css";
import "./admin-desktop-v2650.css";
import "./schedule-clarity-v2651.css";
import "./schedule-clarity-v2652.css";
import "./publication-flow-v2653.css";
import "./admin-command-bar-v2655.css";
import "./public-desktop-v2656.css";
import "./admin-tools-v2666.css";
import "./admin-teams-v2674.css";
import "./public-masterpiece-v2658.css";
import "./reporting-admin-v2664.css";
import "./reporter-v2665.css";
import "./reporter-flow-v2667.css";
import "./public-atmosphere-v2671.css";
import "./public-texttv-v2675.css";
import "./ios-safe-area-v2684.css";
import "./admin-cup-identity-v2685.css";
import "./release-v2697.css";
import { PwaBoot } from "@/components/PwaBoot";
import { ViewModeSwitch } from "@/components/ViewModeSwitch";
import { HeaderShareAction } from "@/components/HeaderShareAction";
import { SiteFooter } from "@/components/SiteFooter";

const APP_VERSION = "2.6.97";

export const metadata: Metadata = {
  title: `CupNavi v${APP_VERSION}`,
  description: "Cuper, matcher och liveinfo – utan krångel.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#101f2a",
  colorScheme: "light",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="sv">
      <body>
        <header className="brandbar">
          <a href="/" className="brand" aria-label="CupNavi startsida">
            <span className="brand-lockup">
              <img className="brand-emblem" src="/cupnavi-emblem-v2642.png" alt="" aria-hidden="true" />
              <span className="brand-title"><strong>CUP</strong><strong>NAVI</strong><small>TURNERINGEN I FICKAN</small></span>
            </span>
          </a>
          <HeaderShareAction />
          <span className="app-version-badge" aria-label={`CupNavi version ${APP_VERSION}`}>v{APP_VERSION}</span>
        </header>
        <PwaBoot />
        <ViewModeSwitch />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
