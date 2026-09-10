import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "CupNavi", description: "Cuper, matcher och liveinfo – utan krångel." };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="sv"><body><header className="brandbar"><a href="/" className="brand">CUP<span>NAVI</span><small>/// MATCHDAY SYSTEM</small></a></header>{children}</body></html>;
}
