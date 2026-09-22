"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";
import {
  CUP_IMPORT_STEPS,
  nextCupImportStep,
  previousCupImportStep,
} from "./cup-import-steps";

const API_BASE = CLIENT_API_BASE;
const TOKEN_KEY = "cupnavi_admin_session_v629";
const CUP_KEY = "cupnavi_admin_active_cup_v651";
const IMPORT_RESUME_KEY = "cupnavi_import_resume_v1";
const IMPORT_WELCOME_KEY = "cupnavi_import_welcome_v1";
const IMPORT_RESUME_MAX_AGE_MS = 24 * 60 * 60 * 1000;

type SessionPayload = { account?: { id?: number } };
type CreatedCup = { id: number; name: string };
type CreatedGroup = { id: number; name: string };
type CreatedTeam = { id: number; name: string; group_id?: number | null };
type ExistingGroup = { id: number; name: string };
type ExistingTeam = { id: number; name: string; group_id?: number | null };
type ImportedTeam = { name: string; group_name?: string | null };
type ImportedMatch = {
  time?: string | null;
  venue?: string | null;
  group_name?: string | null;
  home_team?: string | null;
  away_team?: string | null;
  stage?: string | null;
  duration?: string | null;
};
type ImportedPlayoffMatch = {
  time?: string | null;
  venue?: string | null;
  label?: string | null;
  home_source?: string | null;
  away_source?: string | null;
  duration?: string | null;
};
type ImportProposal = {
  location?: string | null;
  tournament_name?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  venues?: string[];
  teams?: ImportedTeam[];
  matches?: ImportedMatch[];
  playoff_matches?: ImportedPlayoffMatch[];
  rules?: string[];
  rule_values?: Record<string, number | null>;
  playoff_rule_values?: Record<string, number | string | null>;
  warnings?: string[];
};
type ImportResume = {
  version: 1;
  cupId: number;
  fingerprint: string;
  initialRequested: boolean;
  createdAt: number;
};
type SchedulePayload = { match_count: number };
type ImportFailure = { cup: CreatedCup; stage: string; detail: string };

async function request<T>(
  path: string,
  options: RequestInit,
  token: string,
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok)
    throw new Error(
      payload && typeof payload.detail === "string"
        ? payload.detail
        : `API-fel ${response.status}`,
    );
  return payload as T;
}

function normalize(value?: string | null) {
  return (value || "").trim().toLocaleLowerCase("sv");
}
function groupNames(teams: ImportedTeam[]) {
  return [
    ...new Map(
      teams
        .map((t) => (t.group_name || "").trim())
        .filter(Boolean)
        .map((name) => [normalize(name), name]),
    ).values(),
  ];
}
function groupedTeams(teams: ImportedTeam[]) {
  const groups = new Map<string, { name: string; teams: ImportedTeam[] }>();
  const ungrouped: ImportedTeam[] = [];
  for (const team of teams) {
    const name = (team.group_name || "").trim();
    if (!name) {
      ungrouped.push(team);
      continue;
    }
    const key = normalize(name);
    if (!groups.has(key)) groups.set(key, { name, teams: [] });
    groups.get(key)!.teams.push(team);
  }
  return { groups: [...groups.values()], ungrouped };
}
function uniqueImportedTeams(teams: ImportedTeam[]) {
  const byName = new Map<string, ImportedTeam>();
  let duplicateCount = 0;
  const conflictingGroups: string[] = [];
  for (const row of teams) {
    const name = String(row?.name || "").split(/\s+/).filter(Boolean).join(" ");
    if (!name) continue;
    const key = normalize(name);
    const groupName =
      String(row?.group_name || "").split(/\s+/).filter(Boolean).join(" ") ||
      null;
    const existing = byName.get(key);
    if (!existing) {
      byName.set(key, { name, group_name: groupName });
      continue;
    }
    duplicateCount += 1;
    const existingGroup = normalize(existing.group_name);
    const nextGroup = normalize(groupName);
    if (!existingGroup && groupName) existing.group_name = groupName;
    else if (nextGroup && existingGroup && nextGroup !== existingGroup)
      conflictingGroups.push(name);
  }
  return { teams: [...byName.values()], duplicateCount, conflictingGroups };
}
function visibleImportNotes(
  warnings: string[],
  startDate: string,
  endDate: string,
) {
  return warnings.filter((raw) => {
    const warning = raw.toLocaleLowerCase("sv");
    return !(
      Boolean(startDate && endDate) &&
      (warning.includes("årtal") ||
        warning.includes("start_date") ||
        warning.includes("end_date"))
    );
  });
}
function matchNeedsReview(match: ImportedMatch) {
  return (
    !match.time?.trim() ||
    !match.home_team?.trim() ||
    !match.away_team?.trim() ||
    !match.venue?.trim()
  );
}
function matchLabel(match: ImportedMatch, index: number) {
  return (
    [match.home_team?.trim(), match.away_team?.trim()]
      .filter(Boolean)
      .join(" – ") || `Match ${index + 1}`
  );
}
function playoffNeedsReview(match: ImportedPlayoffMatch) {
  return !match.label?.trim() || !match.time?.trim() || !match.venue?.trim();
}
function playoffLabel(match: ImportedPlayoffMatch, index: number) {
  return match.label?.trim() || `Slutspelsmatch ${index + 1}`;
}
function importFingerprint(
  name: string,
  startDate: string,
  endDate: string,
  proposal: ImportProposal,
) {
  return JSON.stringify({
    name: name.trim(),
    startDate,
    endDate,
    teams: (proposal.teams || []).map((t) => [
      normalize(t.name),
      normalize(t.group_name),
    ]),
    matches: (proposal.matches || []).map((m) => [
      m.time || "",
      normalize(m.home_team),
      normalize(m.away_team),
      normalize(m.venue),
      normalize(m.group_name),
    ]),
    playoffMatches: (proposal.playoff_matches || []).map((m) => [
      m.time || "",
      normalize(m.label),
      normalize(m.home_source),
      normalize(m.away_source),
      normalize(m.venue),
    ]),
    venues: (proposal.venues || []).map(normalize),
    location: normalize(proposal.location),
  });
}
function readResume(fingerprint: string): ImportResume | null {
  try {
    const raw = localStorage.getItem(IMPORT_RESUME_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ImportResume;
    if (
      parsed.version !== 1 ||
      parsed.fingerprint !== fingerprint ||
      Date.now() - parsed.createdAt > IMPORT_RESUME_MAX_AGE_MS
    ) {
      localStorage.removeItem(IMPORT_RESUME_KEY);
      return null;
    }
    return parsed;
  } catch {
    localStorage.removeItem(IMPORT_RESUME_KEY);
    return null;
  }
}
function writeResume(value: ImportResume) {
  localStorage.setItem(IMPORT_RESUME_KEY, JSON.stringify(value));
}
function clearResume() {
  localStorage.removeItem(IMPORT_RESUME_KEY);
}
function friendlyImportError(error: unknown) {
  const detail =
    error instanceof Error ? error.message : "Importen kunde inte slutföras.";
  if (/failed to fetch|networkerror|load failed/i.test(detail))
    return "Kontakten med servern bröts";
  if (/aborterror|aborted|stale cup request/i.test(detail))
    return "Anropet avbröts innan servern hann svara";
  if (/redan ett lag med samma namn/i.test(detail))
    return "Ett lag fanns redan i utkastet. CupNavi kan fortsätta och återanvända befintligt lag";
  return detail.replace(/[.\s]+$/, "");
}

export default function CupCreateLauncherV6() {
  const [token, setToken] = useState<string | null>(null),
    [canCreate, setCanCreate] = useState(false),
    [open, setOpen] = useState(false),
    [mode, setMode] = useState<"manual" | "import">("manual");
  const [name, setName] = useState(""),
    [startDate, setStartDate] = useState(""),
    [endDate, setEndDate] = useState(""),
    [files, setFiles] = useState<File[]>([]),
    [proposal, setProposal] = useState<ImportProposal | null>(null),
    [importSchedule, setImportSchedule] = useState(false),
    [importStep, setImportStep] = useState(0),
    [expandedMatch, setExpandedMatch] = useState<number | null>(null),
    [expandedPlayoff, setExpandedPlayoff] = useState<number | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [importFailure, setImportFailure] = useState<ImportFailure | null>(null);
  const rawTeams = proposal?.teams || [];
  const teamDedupe = useMemo(() => uniqueImportedTeams(rawTeams), [rawTeams]);
  const teams = teamDedupe.teams,
    matches = proposal?.matches || [],
    playoffMatches = proposal?.playoff_matches || [],
    groups = useMemo(() => groupNames(teams), [teams]),
    teamBuckets = useMemo(() => groupedTeams(teams), [teams]);
  const notes = useMemo(
    () => visibleImportNotes(proposal?.warnings || [], startDate, endDate),
    [proposal?.warnings, startDate, endDate],
  );
  const matchesToReview = useMemo(
    () =>
      matches.reduce<number[]>((a, m, i) => {
        if (matchNeedsReview(m)) a.push(i);
        return a;
      }, []),
    [matches],
  );
  const playoffsToReview = useMemo(
    () =>
      playoffMatches.reduce<number[]>((a, m, i) => {
        if (playoffNeedsReview(m)) a.push(i);
        return a;
      }, []),
    [playoffMatches],
  );
  const blockers = useMemo(() => {
    const rows: string[] = [];
    if (!name.trim()) rows.push("Cupnamn saknas");
    if (importSchedule && matches.length && !startDate)
      rows.push("Startdatum saknas för matchprogrammet");
    if (importSchedule && matchesToReview.length)
      rows.push(`${matchesToReview.length} matcher är ofullständiga`);
    return rows;
  }, [name, importSchedule, matches.length, startDate, matchesToReview.length]);
  const warnings = useMemo(() => {
    const rows: string[] = [];
    if (teamBuckets.ungrouped.length)
      rows.push(`${teamBuckets.ungrouped.length} lag saknar grupp`);
    if (teamDedupe.duplicateCount)
      rows.push(`${teamDedupe.duplicateCount} dubblettrad med lag slogs ihop`);
    if (teamDedupe.conflictingGroups.length)
      rows.push(
        `${teamDedupe.conflictingGroups.length} lag hade motstridiga grupper i underlaget`,
      );
    if (!groups.length && teams.length) rows.push("Inga grupper hittades");
    return rows;
  }, [
    teamBuckets.ungrouped.length,
    teamDedupe.duplicateCount,
    teamDedupe.conflictingGroups.length,
    groups.length,
    teams.length,
  ]);
  const ready = blockers.length === 0;
  const canStartImport = ready && !importFailure;
  const hasDraft = Boolean(
    name || startDate || endDate || files.length || proposal,
  );

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) return;
    request<SessionPayload>("/api/admin/session", {}, stored)
      .then((data) => {
        if (data.account?.id !== undefined) {
          setToken(stored);
          setCanCreate(true);
        }
      })
      .catch(() => undefined);
  }, []);

  function reset() {
    setMode("manual");
    setName("");
    setStartDate("");
    setEndDate("");
    setFiles([]);
    setProposal(null);
    setImportSchedule(false);
    setImportStep(0);
    setExpandedMatch(null);
    setExpandedPlayoff(null);
    setError("");
    setImportFailure(null);
  }
  function close() {
    if (busy) return;
    if (
      hasDraft &&
      !window.confirm(
        "Du har osparat arbete i den här cupen. Vill du verkligen stänga och kasta det?",
      )
    )
      return;
    setOpen(false);
    reset();
  }
  function goToCup(cup: CreatedCup, step = "overview") {
    localStorage.setItem(CUP_KEY, String(cup.id));
    const url = new URL(window.location.href);
    url.searchParams.set("cup", String(cup.id));
    url.hash = step;
    window.location.assign(`${url.pathname}${url.search}${url.hash}`);
  }
  function updateMatch(index: number, key: keyof ImportedMatch, value: string) {
    setProposal((current) => {
      if (!current) return current;
      const next = [...(current.matches || [])];
      next[index] = { ...next[index], [key]: value || null };
      return { ...current, matches: next };
    });
  }
  function updatePlayoffMatch(
    index: number,
    key: keyof ImportedPlayoffMatch,
    value: string,
  ) {
    setProposal((current) => {
      if (!current) return current;
      const next = [...(current.playoff_matches || [])];
      next[index] = { ...next[index], [key]: value || null };
      return { ...current, playoff_matches: next };
    });
  }

  async function createCup(e: FormEvent) {
    e.preventDefault();
    if (!token || !name.trim()) return;
    if (startDate && endDate && endDate < startDate) {
      setError("Slutdatum kan inte vara före startdatum.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const cup = await request<CreatedCup>(
        "/api/admin/cups",
        {
          method: "POST",
          body: JSON.stringify({
            name: name.trim(),
            start_date: startDate || null,
            end_date: endDate || null,
          }),
        },
        token,
      );
      goToCup(cup);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cupen kunde inte skapas.");
      setBusy(false);
    }
  }
  async function analyzeFiles() {
    if (!token || !files.length) return;
    setBusy(true);
    setError("");
    setProposal(null);
    try {
      const form = new FormData();
      files.forEach((file) => form.append("files", file, file.name));
      const result = await request<ImportProposal>(
        "/api/admin/cup-import/analyze",
        { method: "POST", body: form },
        token,
      );
      setProposal(result);
      setName(result.tournament_name || "");
      setStartDate(result.start_date || "");
      setEndDate(result.end_date || result.start_date || "");
      setImportSchedule(Boolean(result.matches?.length));
      setImportStep(0);
      const first = (result.matches || []).findIndex(matchNeedsReview);
      setExpandedMatch(first >= 0 ? first : null);
      const firstPlayoff = (result.playoff_matches || []).findIndex(
        playoffNeedsReview,
      );
      setExpandedPlayoff(firstPlayoff >= 0 ? firstPlayoff : null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Underlaget kunde inte läsas.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function createFromImport(e: FormEvent) {
    e.preventDefault();
    if (!token || !proposal || !name.trim()) return;
    if (startDate && endDate && endDate < startDate) {
      setError("Slutdatum kan inte vara före startdatum.");
      return;
    }
    if (blockers.length) {
      setImportStep(4);
      setError("Åtgärda blockerande punkter innan cupen skapas.");
      return;
    }
    setBusy(true);
    setError("");
    setImportFailure(null);
    const fingerprint = importFingerprint(name, startDate, endDate, proposal);
    let resume = readResume(fingerprint);
    let cup: CreatedCup | null = null;
    let stage = "skapa cupen";
    try {
      if (resume) {
        stage = "kontrollera det sparade utkastet";
        try {
          const info = await request<{ id: number; name: string }>(
            `/api/admin/cups/${resume.cupId}/cupinfo`,
            {},
            token,
          );
          cup = { id: resume.cupId, name: info.name || name.trim() };
        } catch {
          clearResume();
          resume = null;
        }
      }
      if (!cup) {
        stage = "skapa cupen";
        cup = await request<CreatedCup>(
          "/api/admin/cups",
          {
            method: "POST",
            body: JSON.stringify({
              name: name.trim(),
              start_date: startDate || null,
              end_date: endDate || null,
            }),
          },
          token,
        );
        resume = {
          version: 1,
          cupId: cup.id,
          fingerprint,
          initialRequested: false,
          createdAt: Date.now(),
        };
        writeResume(resume);
      }
      localStorage.setItem(CUP_KEY, String(cup.id));

      stage = "kontrollera lag och grupper";
      const [groupPayload, teamPayload] = await Promise.all([
        request<{ groups: ExistingGroup[] }>(
          `/api/admin/cups/${cup.id}/groups`,
          {},
          token,
        ),
        request<{ teams: ExistingTeam[] }>(
          `/api/admin/cups/${cup.id}/teams`,
          {},
          token,
        ),
      ]);
      const groupIds = new Map<string, number>(
        (groupPayload.groups || []).map((row) => [normalize(row.name), row.id]),
      );
      stage = "spara grupper";
      for (const groupName of groups) {
        const key = normalize(groupName);
        if (groupIds.has(key)) continue;
        const created = await request<CreatedGroup>(
          `/api/admin/cups/${cup.id}/groups`,
          { method: "POST", body: JSON.stringify({ name: groupName }) },
          token,
        );
        groupIds.set(key, created.id);
      }

      const existingTeams = new Map<string, ExistingTeam>(
        (teamPayload.teams || []).map((row) => [normalize(row.name), row]),
      );
      stage = "spara lag";
      for (const row of teams) {
        const key = normalize(row.name);
        if (!key) continue;
        let team = existingTeams.get(key);
        if (!team) {
          try {
            team = await request<CreatedTeam>(
              `/api/admin/cups/${cup.id}/teams`,
              { method: "POST", body: JSON.stringify({ name: row.name }) },
              token,
            );
          } catch (err) {
            if (!/redan ett lag med samma namn/i.test(String(err))) throw err;
            const refreshed = await request<{ teams: ExistingTeam[] }>(
              `/api/admin/cups/${cup.id}/teams`,
              {},
              token,
            );
            for (const existing of refreshed.teams || [])
              existingTeams.set(normalize(existing.name), existing);
            team = existingTeams.get(key);
            if (!team) throw err;
          }
          existingTeams.set(key, team);
        }
        const groupId = row.group_name
          ? groupIds.get(normalize(row.group_name))
          : undefined;
        if (groupId && team.group_id !== groupId) {
          await request(
            `/api/admin/cups/${cup.id}/teams/${team.id}/group`,
            { method: "PUT", body: JSON.stringify({ group_id: groupId }) },
            token,
          );
          team.group_id = groupId;
        }
      }

      const venues = (proposal.venues || []).filter(Boolean);
      stage = "spara planer och regler";
      if (venues.length) {
        await request(
          `/api/admin/cups/${cup.id}/venues/rules`,
          {
            method: "PUT",
            body: JSON.stringify({ pitch_count: venues.length }),
          },
          token,
        );
        for (let i = 0; i < venues.length; i++)
          await request(
            `/api/admin/cups/${cup.id}/venues/pitches/${i + 1}`,
            { method: "PUT", body: JSON.stringify({ name: venues[i] }) },
            token,
          );
      }
      const ruleValues = Object.fromEntries(
        Object.entries(proposal.rule_values || {}).filter(([, v]) => v != null),
      );
      if (Object.keys(ruleValues).length)
        await request(
          `/api/admin/cups/${cup.id}/rules`,
          { method: "PUT", body: JSON.stringify(ruleValues) },
          token,
        );

      let shouldRunInitial = true;
      if (resume?.initialRequested && importSchedule && matches.length) {
        stage = "kontrollera matchprogrammet";
        const schedule = await request<SchedulePayload>(
          `/api/admin/cups/${cup.id}/schedule`,
          {},
          token,
        );
        shouldRunInitial = schedule.match_count === 0;
      }
      if (shouldRunInitial) {
        const checkpoint: ImportResume = { ...resume!, initialRequested: true };
        writeResume(checkpoint);
        resume = checkpoint;
        stage = "spara matchprogrammet";
        await request(
          `/api/admin/cups/${cup.id}/import/initial`,
          {
            method: "POST",
            body: JSON.stringify({
              proposal,
              import_matches: importSchedule && matches.length > 0,
              fallback_date: startDate || null,
            }),
          },
          token,
        );
      }
      clearResume();
      localStorage.setItem(IMPORT_WELCOME_KEY,JSON.stringify({
        cupId:cup.id,
        cupName:cup.name,
        teams:teams.length,
        groups:groups.length,
        matches:importSchedule?matches.length:0,
        venues:(proposal.venues||[]).length,
        playoffs:playoffMatches.length,
      }));
      goToCup(cup,playoffMatches.length?"playoffs":"overview");
    } catch (err) {
      const detail = friendlyImportError(err);
      if (cup) {
        localStorage.setItem(CUP_KEY, String(cup.id));
        setImportFailure({ cup, stage, detail });
        setError("");
      } else setError(`${detail}. Försök igen om en stund.`);
      setBusy(false);
    }
  }

  if (!canCreate) return null;
  const modalStyle = {
    maxWidth: 900,
    width: "min(900px, calc(100vw - 20px))",
    maxHeight: "calc(100dvh - 20px)",
    overflowY: "auto" as const,
    overscrollBehavior: "contain" as const,
  };
  return (
    <>
      <section className="cup-create-toolbar">
        <div>
          <span>MINA CUPER</span>
          <strong>Hantera eller skapa cup</strong>
        </div>
        <button
          type="button"
          onClick={() => {
            reset();
            setOpen(true);
          }}
        >
          Ny cup <span aria-hidden="true">+</span>
        </button>
      </section>
      {open && (
        <div className="cup-create-backdrop">
          <section
            className="cup-create-dialog"
            role="dialog"
            aria-modal="true"
            style={modalStyle}
          >
            <div
              className="cup-create-dialog__head"
              style={{
                position: "sticky",
                top: 0,
                zIndex: 3,
                background: "var(--paper-2,#fbfaf5)",
                paddingBottom: 8,
              }}
            >
              <div>
                <span>NY CUP</span>
                <h2>Hur vill du starta?</h2>
              </div>
              <button
                type="button"
                className="cup-create-close"
                onClick={close}
              >
                ×
              </button>
            </div>
            <p className="cup-create-lead">
              Cupen blir alltid ett utkast först. Import sparar inget förrän du
              granskat resultatet.
            </p>
            <div className="cup-create-mode-tabs" role="tablist" aria-label="Välj hur cupen ska skapas">
              <button
                type="button"
                role="tab"
                aria-selected={mode === "manual"}
                className={mode === "manual" ? "" : "is-secondary"}
                onClick={() => setMode("manual")}
              >
                <span aria-hidden="true">01</span><strong>Skapa manuellt</strong><small>Fyll i själv</small>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === "import"}
                className={mode === "import" ? "" : "is-secondary"}
                onClick={() => setMode("import")}
              >
                <span aria-hidden="true">02</span><strong>Bild eller PDF</strong><small>CupNavi läser</small>
              </button>
            </div>
            {mode === "manual" ? (
              <form onSubmit={createCup}>
                <label>
                  Cupnamn
                  <input
                    autoFocus
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </label>
                <div className="cup-create-dates">
                  <label>
                    Startdatum
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => {
                        setStartDate(e.target.value);
                        if (!endDate) setEndDate(e.target.value);
                      }}
                    />
                  </label>
                  <label>
                    Slutdatum
                    <input
                      type="date"
                      min={startDate || undefined}
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                    />
                  </label>
                </div>
                {error && <p className="cup-create-error">{error}</p>}
                <div className="cup-create-actions">
                  <button
                    type="button"
                    className="is-secondary"
                    onClick={close}
                  >
                    Avbryt
                  </button>
                  <button type="submit" disabled={busy || !name.trim()}>
                    {busy ? "Skapar…" : "Skapa cup"}
                  </button>
                </div>
              </form>
            ) : !proposal ? (
              <>
                <label className="cup-create-file-drop">
                  <span aria-hidden="true">＋</span>
                  <strong>Välj bilder eller PDF</strong>
                  <small>Fotografera ett spelschema eller välj filer från telefonen.</small>
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,image/*,application/pdf,text/plain"
                    onChange={(e) => setFiles(Array.from(e.target.files || []))}
                  />
                </label>
                {!!files.length && <p className="cup-create-file-count"><strong>{files.length}</strong> {files.length===1?"fil vald":"filer valda"}</p>}
                {error && <p className="cup-create-error">{error}</p>}
                <div className="cup-create-actions">
                  <button
                    type="button"
                    className="is-secondary"
                    onClick={close}
                  >
                    Avbryt
                  </button>
                  <button
                    type="button"
                    disabled={busy || !files.length}
                    onClick={() => void analyzeFiles()}
                  >
                    {busy ? "Läser…" : "Läs in underlaget"}
                  </button>
                </div>
              </>
            ) : (
              <form onSubmit={createFromImport}>
                <div className="cup-import-stats">
                  <div>
                    <strong>{teams.length}</strong>
                    <small>Lag</small>
                  </div>
                  <div>
                    <strong>{groups.length}</strong>
                    <small>Grupper</small>
                  </div>
                  <div>
                    <strong>{matches.length}</strong>
                    <small>Matcher</small>
                  </div>
                  <div>
                    <strong>{(proposal.venues || []).length}</strong>
                    <small>Planer</small>
                  </div>
                  <div>
                    <strong>{playoffMatches.length}</strong>
                    <small>Slutspel</small>
                  </div>
                </div>
                <div className="cup-import-steps">
                  {CUP_IMPORT_STEPS.map((step, index) => (
                    <button
                      key={step.id}
                      type="button"
                      className={step.id === importStep ? "" : "is-secondary"}
                      onClick={() => setImportStep(step.id)}
                    >
                      {step.id < importStep ? "✓ " : `${index + 1}. `}
                      {step.label}
                    </button>
                  ))}
                </div>
                {importStep === 0 && (
                  <div>
                    <label>
                      Spelplats eller adress
                      <input value={proposal.location || ""} onChange={e=>setProposal(current=>current ? {...current,location:e.target.value} : current)} placeholder="Spelplats enligt underlaget" />
                    </label>
                    <label>
                      Cupnamn
                      <input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                      />
                    </label>
                    <div className="cup-create-dates">
                      <label>
                        Startdatum
                        <input
                          type="date"
                          value={startDate}
                          onChange={(e) => setStartDate(e.target.value)}
                        />
                      </label>
                      <label>
                        Slutdatum
                        <input
                          type="date"
                          value={endDate}
                          min={startDate || undefined}
                          onChange={(e) => setEndDate(e.target.value)}
                        />
                      </label>
                    </div>
                    {!!(proposal.venues || []).length && (
                      <p>
                        <strong>Planer:</strong>{" "}
                        {(proposal.venues || []).join(", ")}
                      </p>
                    )}
                    {!!(proposal.rules || []).length && (
                      <details>
                        <summary>
                          {proposal.rules!.length} regler hittade
                        </summary>
                        <ul>
                          {proposal.rules!.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                )}
                {importStep === 1 && (
                  <div>
                    <h3>Lag & grupper</h3>
                    {!teams.length ? (
                      <p>Inga lag hittades.</p>
                    ) : (
                      <>
                        <div className="cup-import-group-grid">
                          {teamBuckets.groups.map((group) => (
                            <section
                              className="cup-import-group-card"
                              key={group.name}
                            >
                              <header>
                                <strong>{group.name}</strong>
                                <span>{group.teams.length} lag</span>
                              </header>
                              <ul>
                                {group.teams.map((team, i) => (
                                  <li key={`${team.name}-${i}`}>{team.name}</li>
                                ))}
                              </ul>
                            </section>
                          ))}
                        </div>
                        {!!teamBuckets.ungrouped.length && (
                          <section className="cup-import-ungrouped">
                            <strong>⚠ Ej grupperade</strong>
                            <span>
                              {teamBuckets.ungrouped.length} lag saknar grupp
                            </span>
                            <ul>
                              {teamBuckets.ungrouped.map((team, i) => (
                                <li key={`${team.name}-${i}`}>{team.name}</li>
                              ))}
                            </ul>
                          </section>
                        )}
                      </>
                    )}
                  </div>
                )}
                {importStep === 2 && (
                  <div>
                    <h3>Matcher</h3>
                    <p style={{ fontSize: 13 }}>
                      {matchesToReview.length
                        ? `${matchesToReview.length} matcher behöver kontrolleras.`
                        : "Alla matcher ser kompletta ut."}
                    </p>
                    <div className="cup-import-match-list">
                      {matches.map((match, index) => {
                        const needs = matchNeedsReview(match),
                          expanded = expandedMatch === index;
                        return (
                          <section
                            key={index}
                            className={`cup-import-match-card${needs ? " needs-review" : ""}`}
                          >
                            <button
                              type="button"
                              className="cup-import-match-summary"
                              onClick={() =>
                                setExpandedMatch(expanded ? null : index)
                              }
                            >
                              <span className="cup-import-match-time">
                                {match.time?.trim() || "Tid?"}
                              </span>
                              <span className="cup-import-match-teams">
                                <strong>{matchLabel(match, index)}</strong>
                                <small>
                                  {[match.group_name, match.venue]
                                    .filter(Boolean)
                                    .join(" · ") || "Grupp/plan saknas"}
                                </small>
                              </span>
                              <span
                                className={`cup-import-match-status ${needs ? "warn" : "ok"}`}
                              >
                                {needs ? "Kontrollera" : "✓"}
                              </span>
                            </button>
                            {expanded && (
                              <div className="cup-import-match-editor">
                                <label>
                                  Tid
                                  <input
                                    value={match.time || ""}
                                    onChange={(e) =>
                                      updateMatch(index, "time", e.target.value)
                                    }
                                  />
                                </label>
                                <label>
                                  Grupp
                                  <input
                                    value={match.group_name || ""}
                                    onChange={(e) =>
                                      updateMatch(
                                        index,
                                        "group_name",
                                        e.target.value,
                                      )
                                    }
                                  />
                                </label>
                                <label>
                                  Hemma
                                  <input
                                    value={match.home_team || ""}
                                    onChange={(e) =>
                                      updateMatch(
                                        index,
                                        "home_team",
                                        e.target.value,
                                      )
                                    }
                                  />
                                </label>
                                <label>
                                  Borta
                                  <input
                                    value={match.away_team || ""}
                                    onChange={(e) =>
                                      updateMatch(
                                        index,
                                        "away_team",
                                        e.target.value,
                                      )
                                    }
                                  />
                                </label>
                                <label>
                                  Plan
                                  <input
                                    value={match.venue || ""}
                                    onChange={(e) =>
                                      updateMatch(
                                        index,
                                        "venue",
                                        e.target.value,
                                      )
                                    }
                                  />
                                </label>
                                <button
                                  type="button"
                                  className="cup-import-match-done"
                                  onClick={() => setExpandedMatch(null)}
                                >
                                  Klar
                                </button>
                              </div>
                            )}
                          </section>
                        );
                      })}
                    </div>
                    <label className="cup-import-schedule-toggle">
                      <input
                        type="checkbox"
                        checked={importSchedule}
                        onChange={(e) => setImportSchedule(e.target.checked)}
                      />
                      <span>
                        <strong>Använd matchprogrammet</strong>
                        <small>Importera det granskade schemat</small>
                      </span>
                    </label>
                  </div>
                )}
                {importStep === 3 && (
                  <div>
                    <h3>Slutspel</h3>
                    {!playoffMatches.length ? (
                      <p>Inget slutspel hittades i underlaget.</p>
                    ) : (
                      <>
                        <p style={{ fontSize: 13 }}>
                          {playoffsToReview.length
                            ? `${playoffsToReview.length} slutspelsmatcher behöver kontrolleras.`
                            : "Slutspelsformatet, tiderna och planerna finns i underlaget."}{" "}
                          Deltagare kan vara placeringar eller vinnare från tidigare matcher.
                        </p>
                        <div className="cup-import-match-list">
                          {playoffMatches.map((match, index) => {
                            const needs = playoffNeedsReview(match),
                              expanded = expandedPlayoff === index;
                            return (
                              <section
                                key={index}
                                className={`cup-import-match-card${needs ? " needs-review" : ""}`}
                              >
                                <button
                                  type="button"
                                  className="cup-import-match-summary"
                                  onClick={() =>
                                    setExpandedPlayoff(expanded ? null : index)
                                  }
                                >
                                  <span className="cup-import-match-time">
                                    {match.time?.trim() || "Tid?"}
                                  </span>
                                  <span className="cup-import-match-teams">
                                    <strong>{playoffLabel(match, index)}</strong>
                                    <small>
                                      {[
                                        match.home_source || "Hemma?",
                                        match.away_source || "Borta?",
                                        match.venue,
                                      ]
                                        .filter(Boolean)
                                        .join(" · ")}
                                    </small>
                                  </span>
                                  <span
                                    className={`cup-import-match-status ${needs ? "warn" : "ok"}`}
                                  >
                                    {needs ? "Kontrollera" : "✓"}
                                  </span>
                                </button>
                                {expanded && (
                                  <div className="cup-import-match-editor">
                                    <label>
                                      Matchnamn
                                      <input
                                        value={match.label || ""}
                                        onChange={(e) =>
                                          updatePlayoffMatch(
                                            index,
                                            "label",
                                            e.target.value,
                                          )
                                        }
                                      />
                                    </label>
                                    <label>
                                      Tid
                                      <input
                                        value={match.time || ""}
                                        onChange={(e) =>
                                          updatePlayoffMatch(
                                            index,
                                            "time",
                                            e.target.value,
                                          )
                                        }
                                      />
                                    </label>
                                    <label>
                                      Hemmakälla
                                      <input
                                        value={match.home_source || ""}
                                        onChange={(e) =>
                                          updatePlayoffMatch(
                                            index,
                                            "home_source",
                                            e.target.value,
                                          )
                                        }
                                      />
                                    </label>
                                    <label>
                                      Bortakälla
                                      <input
                                        value={match.away_source || ""}
                                        onChange={(e) =>
                                          updatePlayoffMatch(
                                            index,
                                            "away_source",
                                            e.target.value,
                                          )
                                        }
                                      />
                                    </label>
                                    <label>
                                      Plan
                                      <input
                                        value={match.venue || ""}
                                        onChange={(e) =>
                                          updatePlayoffMatch(
                                            index,
                                            "venue",
                                            e.target.value,
                                          )
                                        }
                                      />
                                    </label>
                                    <button
                                      type="button"
                                      className="cup-import-match-done"
                                      onClick={() => setExpandedPlayoff(null)}
                                    >
                                      Klar
                                    </button>
                                  </div>
                                )}
                              </section>
                            );
                          })}
                        </div>
                        <section className="cup-import-ungrouped">
                          <strong>Slutspel sparas som granskningsunderlag</strong>
                          <span>
                            När cupen är skapad öppnas Slutspel så att format,
                            källor och tider kan godkännas innan trädet skapas.
                          </span>
                        </section>
                      </>
                    )}
                  </div>
                )}
                {importStep === 4 && (
                  <div className="cup-import-final">
                    <section
                      className={`cup-import-readiness ${importFailure ? "is-paused" : ready ? "is-ready" : "needs-action"}`}
                    >
                      <div className="cup-import-readiness-icon">
                        {importFailure ? "↻" : ready ? "✓" : "!"}
                      </div>
                      <div>
                        <span>SLUTKONTROLL</span>
                        <h3>
                          {importFailure
                            ? "Importen pausades"
                            : ready
                              ? "Redo att skapa"
                              : "Behöver åtgärdas"}
                        </h3>
                        <p>
                          {importFailure
                            ? `Utkastet ${importFailure.cup.name} finns sparat. Fortsättningen kontrollerar vad som redan har lagts in.`
                            : ready
                            ? "CupNavi har tillräckligt med verifierad information för att skapa cupen."
                            : "Åtgärda blockerande punkter innan cupen skapas."}
                        </p>
                      </div>
                    </section>
                    <div className="cup-import-checklist">
                      <div className="ok">
                        <strong>✓ Cupinfo</strong>
                        <span>
                          {name || "Cupnamn saknas"}
                          {startDate ? ` · ${startDate}` : ""}
                        </span>
                      </div>
                      <div
                        className={teamBuckets.ungrouped.length ? "warn" : "ok"}
                      >
                        <strong>
                          {teamBuckets.ungrouped.length ? "!" : "✓"} Lag &
                          grupper
                        </strong>
                        <span>
                          {teams.length} lag · {groups.length} grupper
                          {teamBuckets.ungrouped.length
                            ? ` · ${teamBuckets.ungrouped.length} utan grupp`
                            : ""}
                        </span>
                      </div>
                      <div
                        className={
                          importSchedule && matchesToReview.length
                            ? "block"
                            : "ok"
                        }
                      >
                        <strong>
                          {importSchedule && matchesToReview.length ? "!" : "✓"}{" "}
                          Matcher
                        </strong>
                        <span>
                          {matches.length} matcher ·{" "}
                          {importSchedule
                            ? "schemat importeras"
                            : "schemat importeras inte"}
                        </span>
                      </div>
                      <div className="ok">
                        <strong>✓ Planer & regler</strong>
                        <span>
                          {(proposal.venues || []).length} planer ·{" "}
                          {(proposal.rules || []).length} regler
                        </span>
                      </div>
                      <div
                        className={playoffsToReview.length ? "warn" : "ok"}
                      >
                        <strong>
                          {playoffsToReview.length ? "!" : "✓"} Slutspel
                        </strong>
                        <span>
                          {playoffMatches.length
                            ? `${playoffMatches.length} slutspelsmatcher · sparas för separat granskning`
                            : "inget slutspel hittat"}
                        </span>
                      </div>
                    </div>
                    {!!blockers.length && (
                      <section className="cup-import-blockers">
                        <strong>Blockerar skapande</strong>
                        <ul>
                          {blockers.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </section>
                    )}
                    {!!warnings.length && (
                      <section className="cup-import-warnings">
                        <strong>Bra att kontrollera</strong>
                        <ul>
                          {warnings.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </section>
                    )}
                    {!!notes.length && (
                      <details className="cup-import-notes">
                        <summary>
                          Noteringar från avläsningen ({notes.length})
                        </summary>
                        <ul>
                          {notes.map((n, i) => (
                            <li key={i}>{n}</li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                )}
                {importFailure && (
                  <section className="cup-import-recovery" role="alert">
                    <strong>Kunde inte {importFailure.stage}</strong>
                    <p>{importFailure.detail}. Inget behöver göras om från början.</p>
                  </section>
                )}
                {error && <p className="cup-create-error">{error}</p>}
                <div
                  className="cup-create-actions"
                  style={{
                    position: "sticky",
                    bottom: 0,
                    zIndex: 3,
                    background: "var(--paper-2,#fbfaf5)",
                    paddingTop: 10,
                  }}
                >
                  {importStep === 0 ? (
                    <button
                      type="button"
                      className="is-secondary"
                      onClick={() => {
                        setProposal(null);
                        setError("");
                      }}
                    >
                      ← Byt filer
                    </button>
                  ) : importFailure ? (
                    <button
                      type="button"
                      className="is-secondary"
                      onClick={() => goToCup(importFailure.cup)}
                    >
                      Öppna utkastet
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="is-secondary"
                      onClick={() =>
                        setImportStep(previousCupImportStep(importStep))
                      }
                    >
                      ← Tillbaka
                    </button>
                  )}
                  {importStep !== 4 ? (
                    <button
                      type="button"
                      disabled={busy || (importStep === 0 && !name.trim())}
                      onClick={() =>
                        setImportStep(nextCupImportStep(importStep))
                      }
                    >
                      Nästa →
                    </button>
                  ) : (
                    <button
                      type="submit"
                      disabled={busy || (!ready && !importFailure)}
                    >
                      {busy
                        ? importFailure
                          ? "Fortsätter…"
                          : "Importerar…"
                        : importFailure
                          ? "Fortsätt importen"
                          : canStartImport
                          ? "✓ Skapa cup"
                          : "Åtgärda först"}
                    </button>
                  )}
                </div>
              </form>
            )}
          </section>
        </div>
      )}
    </>
  );
}
