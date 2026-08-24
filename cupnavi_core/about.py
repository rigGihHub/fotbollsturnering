"""Public product information for CupNavi.

The About page renders from this catalog instead of duplicating marketing copy in app.py.
When a user-facing capability is added or materially changed, update FEATURE_CATALOG in
that release. This keeps the public About page and product capabilities in one place.
"""

FEATURE_CATALOG = (
    {
        "id": "smart_scheduling",
        "category": "organizer",
        "sv_title": "Smart schemaläggning",
        "en_title": "Smart scheduling",
        "sv": "Skapa och optimera spelscheman med hänsyn till vila, planer, domare, slutspel och fairness.",
        "en": "Build and optimize schedules around rest, venues, officials, playoffs and fairness.",
    },
    {
        "id": "multisport",
        "category": "platform",
        "sv_title": "Byggd för flera sporter",
        "en_title": "Built for multiple sports",
        "sv": "Sportspecifika matchformat, regler och statistik gör plattformen användbar långt utanför fotboll.",
        "en": "Sport-specific match formats, rules and statistics make the platform useful far beyond football.",
    },
    {
        "id": "live_public",
        "category": "audience",
        "sv_title": "En enkel publikupplevelse",
        "en_title": "A simple spectator experience",
        "sv": "Matcher, resultat, tabeller, slutspel, information, favoritlag och informationsskärm samlas på en mobilvänlig plats.",
        "en": "Fixtures, results, standings, playoffs, information, favourite teams and display mode live in one mobile-friendly experience.",
    },
    {
        "id": "team_portal",
        "category": "teams",
        "sv_title": "Egen lagportal",
        "en_title": "Dedicated team portal",
        "sv": "Lag kan checka in, hantera trupp och matchtrupper, läsa meddelanden och kommunicera med arrangör och andra lag.",
        "en": "Teams can check in, manage squads and match rosters, read messages and communicate with organizers and other teams.",
    },
    {
        "id": "control_center",
        "category": "organizer",
        "sv_title": "Control Center för cupdagen",
        "en_title": "Tournament-day Control Center",
        "sv": "Samla avvikelser, förseningar, incheckning, domarläge och incidenter i en operativ vy.",
        "en": "Bring disruptions, delays, check-ins, referee status and incidents together in one operational view.",
    },
    {
        "id": "reporting",
        "category": "officials",
        "sv_title": "Snabb matchrapportering",
        "en_title": "Fast match reporting",
        "sv": "Separata rapportörsflöden minskar risken att officiella resultat och matchhändelser blandas ihop med administration.",
        "en": "Dedicated reporting flows keep official scores and match events separate from tournament administration.",
    },
    {
        "id": "history",
        "category": "platform",
        "sv_title": "Cuphistorik som lever vidare",
        "en_title": "Tournament history that remains",
        "sv": "Avslutade turneringar kan ligga kvar publikt med resultat, tabeller och statistik i stället för att försvinna.",
        "en": "Completed tournaments can remain publicly available with results, standings and statistics instead of disappearing.",
    },
    {
        "id": "accessibility",
        "category": "platform",
        "sv_title": "Tillgänglighet från grunden",
        "en_title": "Accessibility by design",
        "sv": "Stora klickytor, tangentbordsfokus, kontrastläge, skärmläsarstöd och en design som inte förlitar sig på färg ensam.",
        "en": "Large touch targets, keyboard focus, high-contrast mode, screen-reader support and a design that never relies on color alone.",
    },
    {
        "id": "privacy",
        "category": "platform",
        "sv_title": "Integritet för deltagare",
        "en_title": "Participant privacy",
        "sv": "Spelarnamn kan skyddas från publik visning samtidigt som behöriga roller fortfarande kan arbeta med rätt uppgifter.",
        "en": "Player names can be protected from public display while authorized roles retain the information they need.",
    },
    {
        "id": "final_ranking",
        "category": "audience",
        "sv_title": "Slutlig ranking för hela cupen",
        "en_title": "Final tournament ranking",
        "sv": "Arrangören kan välja en slutlig 1–N-ranking av alla lag baserad på slutspelsplacering och gruppresultat.",
        "en": "Organizers can enable a final 1–N ranking of all teams based on playoff placement and group results.",
    },
    {
        "id": "sharing",
        "category": "audience",
        "sv_title": "Enkelt att hitta och dela",
        "en_title": "Easy to find and share",
        "sv": "Permanenta cuplänkar, QR-koder, delning, planfilter och favoritlag gör rätt information lätt att hitta.",
        "en": "Permanent tournament links, QR codes, sharing, venue filters and favourite teams make the right information easy to reach.",
    },
)


def feature_catalog(language="sv"):
    language = "en" if language == "en" else "sv"
    return [
        {
            "id": item["id"],
            "category": item["category"],
            "title": item[f"{language}_title"],
            "description": item[language],
        }
        for item in FEATURE_CATALOG
    ]


def about_intro(language="sv"):
    if language == "en":
        return {
            "title": "About CupNavi",
            "lead": "CupNavi helps organizers run tournaments and gives teams, officials and spectators one clear place to follow them.",
            "vision": "The goal is simple: less tournament administration, fewer avoidable mistakes and a better tournament day for everyone involved.",
        }
    return {
        "title": "Om CupNavi",
        "lead": "CupNavi hjälper arrangörer att genomföra turneringar och ger lag, funktionärer och publik en tydlig plats att följa dem på.",
        "vision": "Målet är enkelt: mindre administration, färre onödiga fel och en bättre cupdag för alla som deltar.",
    }
