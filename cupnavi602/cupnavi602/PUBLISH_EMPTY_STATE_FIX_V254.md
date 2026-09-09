# v1.254 – Publiceringsknapp + tomt lagläge

- Huvudknappen för publicering ligger nu ensam längst till vänster.
- Första publiceringen heter **Publicera**.
- När cupen någon gång har publicerats heter samma primära åtgärd **Uppdatera**.
- Detta fungerar även om cupen avpubliceras senare, via ett beständigt `published_once`-fält.
- **Avpublicera** ligger under *Fler publiceringsval* när cupen är publicerad och konkurrerar inte visuellt med huvudåtgärden.
- TypeError i `Skapade lag` är rättad: `render_empty_state()` kräver `symbol=` som keyword-only argument.
