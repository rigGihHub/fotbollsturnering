# CupNavi v586 – Multi-match revision repair

- Revisionsmotorn kan nu föreslå en gemensam lösning där två eller tre beroende ospelade matcher justeras tillsammans.
- Sökningen är avsiktligt begränsad till kända planer och små tidsförskjutningar i 5-minuterssteg inom ±60 minuter.
- Ett förslag visas bara när hela den markerade revisionskombinationen blir fri från blockerande konflikter i samma konsekvenskontroll som används före databaswrite.
- Admin ser varje matchändring i lösningspaketet och väljer uttryckligen **Använd hela lösningen i granskningen**.
- Valet ändrar endast sessionens förhandsgranskning. Ingen match sparas förrän **Tillämpa valda matchändringar** används.
- Spelade/startade matcher förblir låsta och kan inte ingå i reparationsplanen.
- Om ingen liten gemensam lösning hittas används v585:s enskilda lösningsförslag som fallback; därefter hänvisas till Schema för större omplanering.
