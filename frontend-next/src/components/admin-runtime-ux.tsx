"use client";

import { useEffect } from "react";

export default function AdminRuntimeUx() {
  useEffect(() => {
    let frame = 0;
    let unlockTimer: number | null = null;

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
        const top = statusPanel.querySelector<HTMLElement>(".admin-panel__top strong");
        if (top) top.textContent = "LIVE · KVALITETSKOLL";
        statusPanel.querySelectorAll<HTMLElement>(".admin-checks small").forEach(item => {
          if (item.textContent?.trim() === "Ej klar") item.textContent = "Kan kompletteras";
        });
      }

      // Owner controls used to inherit a global busy flag from unrelated background work.
      // If the page is otherwise interactive, release those controls so destructive actions
      // do not remain permanently disabled after a transient request.
      if (unlockTimer) window.clearTimeout(unlockTimer);
      unlockTimer = window.setTimeout(() => {
        const workspace = document.querySelector(".admin-workspace");
        const activeCup = document.querySelector(".admin-sidebar__cup strong")?.textContent?.trim();
        if (!workspace || !activeCup || activeCup === "Ingen cup") return;
        document.querySelectorAll<HTMLButtonElement>(".admin-remove-cup, .admin-trash-button").forEach(button => {
          if (button.disabled) button.disabled = false;
        });
      }, 900);
    }

    const observer = new MutationObserver(() => {
      if (!frame) frame = window.requestAnimationFrame(apply);
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["disabled"] });
    apply();
    return () => {
      observer.disconnect();
      if (frame) window.cancelAnimationFrame(frame);
      if (unlockTimer) window.clearTimeout(unlockTimer);
    };
  }, []);

  return null;
}
