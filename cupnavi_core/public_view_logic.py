"""Pure public-view navigation logic.

No Streamlit/database imports by design. This keeps public URL routing and
navigation behavior independently testable.
"""

PUBLIC_PAGE_SPECS = (
    ("Matcher", "matches", "Matcher", "Matcher"),
    ("Mitt lag", "team", "Mitt lag", "Mitt lag"),
    ("Tabeller", "tables", "Tabell", "Tabell"),
    ("Slutspel", "playoffs", "Slutspel", "Slutspel"),
    ("Info", "info", "Information", "Info"),
)

PUBLIC_SECTION_TO_PAGE = {section: page for page, section, _, _ in PUBLIC_PAGE_SPECS}
# Existing shared links using ?section=stats remain useful after Statistik moved
# under Tabell; route them to the nearest surviving public destination.
PUBLIC_SECTION_TO_PAGE["stats"] = "Tabeller"
PUBLIC_PAGE_TO_SECTION = {page: section for page, section, _, _ in PUBLIC_PAGE_SPECS}


def resolve_public_page(requested_section="", current_page=None):
    """Resolve active public page with URL > valid session > schedule fallback."""
    requested = str(requested_section or "").strip().lower()
    if requested in PUBLIC_SECTION_TO_PAGE:
        return PUBLIC_SECTION_TO_PAGE[requested]
    if current_page in PUBLIC_PAGE_TO_SECTION:
        return current_page
    return "Matcher"


def public_section_for_page(page):
    """Return canonical query-string section for a public page."""
    return PUBLIC_PAGE_TO_SECTION.get(page, "matches")


def public_navigation_specs():
    """Return the immutable public navigation definitions."""
    return PUBLIC_PAGE_SPECS
