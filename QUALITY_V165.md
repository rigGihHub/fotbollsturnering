# QUALITY V165
Release: 2026.08.25-165-PUBLIC-PAGE-ORDER-FIX

Root cause confirmed from the persisted error-id algorithm:
CN-AABCB9 is the UnboundLocalError raised when public_page is read before assignment
inside render_public_view.

Fix:
- moved the Information-screen page check until after public_page is resolved
- added a regression reproducing the exact CN-AABCB9 id
- added assignment-before-read ordering guard
