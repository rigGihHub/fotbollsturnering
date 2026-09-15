import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./ux-polish.css";
import "./ux-v262.css";
import "./ux-v265.css";
import "./admin-step-flow.css";
import "./ui-system-v2615.css";
import "./mode-switch-v2615.css";
import "./ui-system-v2616.css";
import "./public-ux-v2624.css";
import "./comic-card-v2634.css";
import "./public-system-v2639.css";
import "./brand-v2641.css";
import "./admin-guide-v2643.css";
import "./beginner-flow-v2645.css";
import { PwaBoot } from "@/components/PwaBoot";
import { ViewModeSwitch } from "@/components/ViewModeSwitch";

const APP_VERSION = "2.6.53";

export const metadata: Metadata = {
  title: `CupNavi v${APP_VERSION}`,
  description: "Cuper, matcher och liveinfo – utan krångel.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
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
          <span className="app-version-badge" aria-label={`CupNavi version ${APP_VERSION}`}>v{APP_VERSION}</span>
        </header>
        <PwaBoot />
        <ViewModeSwitch />
        {children}
      </body>
    </html>
  );
}
