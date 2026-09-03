# CupNavi v407 – Safe next match flow

Efter ett färdigt resultat från Cupdagen kan funktionären nu starta den exakta nästa matchen på samma plan direkt från resultatkvittot. Direktstart visas bara när matchen fortfarande är `not_started` och planerad avspark är högst 10 minuter bort eller redan passerad. Annars öppnas Cupdagen som tidigare. Statusändringen använder samma optimistiska låsning som övriga matchstatusflöden. Ingen ny databasfråga läggs till.
