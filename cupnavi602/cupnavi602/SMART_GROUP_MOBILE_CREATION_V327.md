# v327 – Smart Group + Mobile Creation

- New tournament creation is reusable in sidebar and main Admin content.
- Empty Admin state exposes the creation form directly, so mobile users are not dependent on the hidden sidebar.
- Existing tournaments also show a compact main-content “Ny turnering” expander.
- Smart Group Setup previews deterministic, size-balanced groups per competition class before writing.
- Automatic group creation is atomic and aborts if groups or team class/group state changed concurrently.
- Manual group editing remains available before schedule generation.
