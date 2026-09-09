# v413 – Team portal session revocation

## Problem
A team portal session stayed authenticated after an administrator regenerated the team access code. The new code protected new logins, but an already open browser session could retain access.

## Change
Team portal authentication now stores the credential hash used at login. On every portal render, CupNavi compares that hash with the current credential for the same tournament and team before exposing team-scoped data or actions. If the code was regenerated or removed, the old session is cleared immediately and the user must log in again.

## Why this release
This closes a real authorization lifecycle gap without adding UI or product complexity. It follows the server-side permission audit priority from the product handover.
