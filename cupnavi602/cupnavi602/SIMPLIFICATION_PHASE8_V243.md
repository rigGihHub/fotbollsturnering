# CupNavi v.1.243 – Simplification Phase 8

## Scope
This pass simplifies:
- Besöksstatistik
- Cupverktyg
- Statistiktopplistor / Skytteligor

No analytics collection, scheduling mutation, audit/undo, venue data or statistics
calculation logic was removed.

## Besöksstatistik
The default view now focuses on period selection and headline metrics:
- unique sessions;
- page views;
- visits today;
- page views today;
- active sessions.

Secondary analysis is progressively disclosed:
- **Utveckling över tid**
- **Enheter, webbläsare & trafikkällor**
- **Senaste besök & integritet**

Privacy behavior is unchanged: CupNavi does not store visitor IP addresses.

## Cupverktyg
The page is framed as optional operational tooling rather than a normal workflow step.

Tab labels were simplified:
- Status
- Flytta match
- Försening
- Slutspel
- Karta & QR
- Historik
- Summering

Secondary details are now collapsed:
- quality deductions under **Förbättringspunkter**;
- delay preview under **Förhandsvisa ändrade tider**;
- registered venue points and deletion under **Visa eller ta bort platser**;
- audit log and undo controls under **Visa historik & ångra**.

All schedule-change validation, notifications, audit writes and undo safeguards remain.

## Topplistor
The page is now called **Topplistor**.

The goal leaderboard remains directly visible when enabled. Secondary statistics are
collapsed:
- Assistliga
- Gula/röda kort

The underlying statistics queries and sorting rules are unchanged.

## Test contracts
The visitor analytics source contract was updated so it protects the presence of the
recent-visit detail while allowing its new progressive-disclosure presentation.
