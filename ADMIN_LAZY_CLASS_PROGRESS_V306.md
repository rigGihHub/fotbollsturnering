# CupNavi v1.306 — Admin lazy class progress

Adminöversikt no longer performs the per-class team-count query on every rerun just because **Förberedelser i detalj** exists as a collapsed expander.

Streamlit expanders are not lazy. The detailed class distribution is now behind **Visa lagfördelning per klass** and the grouped team-count query only runs when the organizer explicitly asks for that detail.

This preserves the information while making the default Adminöversikt path cheaper and visually calmer.

No tournament rules, schedule generation, result handling, publication, authentication, schema, or concurrency behavior changed.
