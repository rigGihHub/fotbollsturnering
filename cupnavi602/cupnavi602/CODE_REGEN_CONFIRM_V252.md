# v1.252 – Säker regenerering av åtkomstkoder

- Matchrapportör och domare kan få nya fyrsiffriga koder.
- Om en kod redan finns krävs en uttrycklig bekräftelse innan den ersätts.
- Admin kan regenerera **alla lagkoder samtidigt**.
- Massåtgärden visar antal berörda lag och varnar att alla gamla koder slutar fungera.
- Även regenerering av ett enskilt lags kod kräver bekräftelse.
- Första skapandet av en kod är inte destruktivt och kräver därför ingen extra bekräftelse.
- Massrotation av lagkoder görs i en databastransaktion och lagras fortsatt saltat/hashat.
