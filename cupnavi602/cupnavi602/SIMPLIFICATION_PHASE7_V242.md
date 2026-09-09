# CupNavi v.1.242 – Simplification Phase 7

## Scope
This pass simplifies four secondary Admin areas:
- Sponsorer
- Erbjudanden
- Funktionärer
- Import

No persistence, concurrency, validation or transactional import logic was removed.

## Sponsorer
The normal add flow now asks only for:
- sponsor name;
- whether it should be public immediately.

Secondary data lives under **Fler sponsoruppgifter**:
- sponsor level;
- website;
- display order;
- logo;
- description.

The redundant "Befintliga sponsorer" heading was replaced by a compact count. Existing sponsor edit/delete expanders remain unchanged.

## Erbjudanden
The default add flow now focuses on:
- title;
- business/restaurant;
- public visibility.

Code, expiry, URL, display order and conditions are under **Fler erbjudandeuppgifter**.
Existing optimistic update/delete safeguards remain unchanged.

## Funktionärer
The default form now asks for **Namn** and **Roll** first.
Plan, phone, email, public contact and notes are under **Fler funktionärsuppgifter**.

The duplicate always-visible functionary table is collapsed under **Visa funktionärslista**.
The complete work-shift area is now under **Funktionärsschema & arbetspass**.

## Import
The decorative five-step progress strip was removed. The flow remains guided, but only relevant controls are visible.

- file upload remains first;
- column mapping is under **Kolumnmappning** and opens automatically only when required fields could not be auto-matched;
- review metrics remain visible;
- detailed issue rows are under **Visa importdetaljer** and open automatically when blocking errors exist;
- preview and explicit final confirmation remain intact.

Atomic team/player import behavior is preserved:
- local SQLite uses `BEGIN IMMEDIATE`;
- failures roll back;
- team limit is rechecked inside the write transaction;
- team import still marks the schedule dirty and unpublishes the cup.
