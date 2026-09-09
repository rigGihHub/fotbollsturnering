# v380 – Publika matchkort

- Publika matchkort prioriterar nu tid, plan och matchstatus allra högst.
- Matchfas och faktiskt matchnummer visas separat och lugnare.
- Hemma- och bortalag har tydligare visuell hierarki, med resultat/VS centrerat.
- Kommande matcher inom tre timmar visar relativ tid, exempelvis “om 35 min”.
- Pågående, kommande och färdigspelade matcher har egna diskreta visuella tillstånd.
- Pågående matcher får en tydlig röd vänsterindikator utan att hela kortet blir visuellt tungt.
- Färdigspelade matcher tonas ned så kommande/live-matcher får mer uppmärksamhet.
- Domare, väder och matchställ ligger fortsatt sekundärt.
- Matchnumret använder nu matchens riktiga match_no när det finns, i stället för listpositionen.
- Mobilkort har mindre padding och bättre informationsdensitet.
- Ingen ny databasfråga, datamodell eller skrivlogik.
- Databasschema fortsatt v30.
