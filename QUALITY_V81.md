# CupNavi 2026.08.21-81-PERFORMANCE-POLISH

- Messenger använder nu Web Share API. På mobil öppnas telefonens delningsmeny där Messenger kan väljas.
  Om Web Share saknas kopieras cupens direktlänk som fallback.
- Engelskan har byggts ut med ett generellt översättningslager för rubriker, knappar, formulär,
  statusmeddelanden, select/radio-visning, data-editor-rubriker och vanliga tabeller.
- Publikvyn batchhämtar lag och matchhändelser i stället för att göra separata frågor per match.
- Besöksstatistiken gör inga databasfrågor eller skrivningar mellan 60-sekunders mätpunkter.
