import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./ux-polish.css";
import { PwaBoot } from "@/components/PwaBoot";

const APP_VERSION = "2.6.1";

export const metadata: Metadata = {
  title: `CupNavi v${APP_VERSION}`,
  description: "Cuper, matcher och liveinfo – utan krångel.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#f4f1e8",
  colorScheme: "light",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="sv">
      <body>
        <header className="brandbar">
          <a href="/" className="brand">CUP<span>NAVI</span><small>/// MATCHDAY SYSTEM</small></a>
          <span className="app-version-badge" aria-label={`CupNavi version ${APP_VERSION}`}>v{APP_VERSION}</span>
        </header>
        <PwaBoot />
        {children}
      </body>
    </html>
  );
}
