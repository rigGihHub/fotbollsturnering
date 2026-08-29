"""Presentation for tournament-scoped reporter/referee access codes."""
from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any


def render_role_code_card(
    st: Any,
    label: str,
    table_name: str,
    session_prefix: str,
    tournament_id: int,
    credential: Any,
    rotate_code: Callable[[str], str],
) -> None:
    """Render one role-code card while delegating credential writes to the app layer."""
    with st.container(border=True):
        st.markdown(f"**{label}**")
        if credential:
            st.caption(
                "Kod aktiv"
                + (
                    f" · ändrad {str(credential['rotated_at']).replace('T',' ')}"
                    if credential["rotated_at"]
                    else ""
                )
            )
        else:
            st.caption("Ingen kod skapad ännu.")

        code_key = f"new_{session_prefix}_code_{tournament_id}"
        confirm_key = f"confirm_regenerate_{session_prefix}_code_{tournament_id}"

        if not credential:
            create_requested = st.button(
                "Generera 4-siffrig kod",
                key=f"generate_{session_prefix}_code_{tournament_id}",
                type="primary",
                use_container_width=True,
            )
        else:
            create_requested = False
            if not st.session_state.get(confirm_key):
                if st.button(
                    "Regenerera ny kod",
                    key=f"request_regenerate_{session_prefix}_code_{tournament_id}",
                    use_container_width=True,
                ):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                st.warning(
                    f"Är du säker? Den nuvarande koden för {label.lower()} slutar fungera direkt."
                )
                yes_col, no_col = st.columns(2)
                if yes_col.button(
                    "Ja, regenerera",
                    key=f"confirm_regenerate_{session_prefix}_{tournament_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    create_requested = True
                    st.session_state.pop(confirm_key, None)
                if no_col.button(
                    "Avbryt",
                    key=f"cancel_regenerate_{session_prefix}_{tournament_id}",
                    use_container_width=True,
                ):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()

        if create_requested:
            st.session_state[code_key] = rotate_code(table_name)
            st.rerun()

        if st.session_state.get(code_key):
            st.markdown(
                f"<div style='font-size:2rem;font-weight:900;letter-spacing:.22em;"
                f"text-align:center;padding:12px;border:1px solid #d9e2dd;border-radius:12px;"
                f"background:#fff'>{html.escape(st.session_state[code_key])}</div>",
                unsafe_allow_html=True,
            )
            st.caption("Kopiera eller dela koden nu. Den visas bara efter generering.")
