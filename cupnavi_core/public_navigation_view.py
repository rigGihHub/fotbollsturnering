"""Pure HTML builder for the public CupNavi section navigation.

Framework-agnostic by design: no Streamlit or database imports. The caller
provides the navigation specs and translation function so routing behaviour
remains owned by ``public_view_logic`` while HTML generation is independently
testable.
"""

from __future__ import annotations

import html
from urllib.parse import quote


def build_public_navigation_html(
    navigation_specs,
    *,
    current_page: str,
    public_slug,
    requested_team_id=None,
    translate=lambda value: value,
) -> str:
    """Build the single responsive public navigation bar.

    ``public_slug`` is URL-encoded here so callers cannot accidentally produce
    malformed navigation links. Team selection is preserved only when a valid
    team id is supplied.
    """
    cup_key = quote(str(public_slug or ""))
    team_query = ""
    if requested_team_id is not None:
        try:
            team_query = f"&team={int(requested_team_id)}"
        except (TypeError, ValueError):
            team_query = ""

    links = []
    for page_value, section, desktop_label, mobile_label in navigation_specs:
        active_class = "active" if current_page == page_value else ""
        desktop_text = desktop_label if desktop_label == "Cupinfo" else translate(desktop_label)
        mobile_text = mobile_label if mobile_label == "Cupinfo" else translate(mobile_label)
        href = f"?cup={cup_key}&section={quote(str(section))}{team_query}"
        links.append(
            f"<a role='button' class='{active_class}' href='{html.escape(href, quote=True)}'>"
            f"<span class='cn-nav-desktop'>{html.escape(str(desktop_text))}</span>"
            f"<span class='cn-nav-mobile'>{html.escape(str(mobile_text))}</span></a>"
        )

    return (
        "<nav class='cn-mobile-bottom-nav cn-public-section-nav' aria-label='Cup navigation'>"
        + "".join(links)
        + "</nav>"
    )
