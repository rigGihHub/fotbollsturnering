"use client";

import { useEffect } from "react";

export default function AdminRuntimeUx() {
  useEffect(() => {
    let frame = 0;

    function apply() {
      frame = 0;
      document.querySelectorAll<HTMLElement>(".admin-main > .admin-panel").forEach(panel => {
        const strong = panel.querySelector("strong");
        const paragraph = panel.querySelector("p");
        if (strong?.textContent?.trim() === "Kunde inte genomföra ändringen" && paragraph?.textContent?.trim() === "Failed to fetch") {
          panel.classList.add("admin-transient-error");
          strong.textContent = "Tillfälligt anslutningsproblem";
          paragraph.textContent = "CupNavi tappade kontakten med servern. Din cup är kvar – försök igen när anslutningen är tillbaka.";
        }
      });

      const published = document.querySelector(".admin-draft")?.textContent?.includes("PUBLICERAD") ?? false;
      const statusPanel = document.querySelector<HTMLElement>(".admin-panel--status");
      if (published && statusPanel) {
        const heading = statusPanel.querySelector("h2");
        if (heading?.textContent === "Cupen är publicerad") heading.textContent = "Cupen är publicerad";
        const top = statusPanel.querySelector<HTMLElement>(".admin-panel__top strong");
        if (top) top.textContent = "LIVE · KVALITETSKOLL";
        statusPanel.querySelectorAll<HTMLElement>(".admin-checks small").forEach(item => {
          if (item.textContent?.trim() === "Ej klar") item.textContent = "Kan kompletteras";
        });
      }
    }

    const observer = new MutationObserver(() => {
      if (!frame) frame = window.requestAnimationFrame(apply);
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    apply();
    return () => {
      observer.disconnect();
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, []);

  return null;
}
