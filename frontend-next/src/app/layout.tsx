import type { Metadata, Viewport } from "next";
import "./globals.css";
import { PwaBoot } from "@/components/PwaBoot";

export const metadata: Metadata = {
  title: "CupNavi",
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
        </header>
        <PwaBoot />
        {children}
      </body>
    </html>
  );
}
