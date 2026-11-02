# Kostenkarte — gemessen, nicht geschätzt

**Stand 02.09.2026.** Quelle: `~/.claude/projects/` — 383 Haupt-Transcripts (822 MB),
229 Subagenten-Transcripts (156 MB), 13.145 auswertbare Werkzeug-Turns, 950 Arbeitsblöcke,
359 Sessions mit Messwert.

## Verfahren

Kontextstand einer Antwort:
`ctx = input_tokens + cache_creation_input_tokens + cache_read_input_tokens`
der Assistant-Zeile. Verifiziert über die Kette: `cache_read(n+1) = cache_read(n) + cache_creation(n)`.

Kosten eines Werkzeugs: `Kosten(n) = ctx(n+1) − ctx(n) − output_tokens(n)`,
nur Turns mit genau einem Werkzeugaufruf und ohne dazwischenliegenden Nutzertext,
negative Deltas (Kompaktierung) verworfen.

⚠️ Drei Filter, jeder einzeln nötig:
- `type == "assistant"` — nur diese Zeilen tragen `usage`
- `model != "<synthetic>"` — 70 solche Zeilen existieren, `usage` mit lauter Nullen
- `isSidechain != true` — sonst misst man einen Subagenten statt des Hauptthreads

Und: Eine API-Antwort erzeugt **mehrere** JSONL-Zeilen (thinking / text / tool_use) mit
identischer `usage`. Für „letzter Wert" harmlos, für Summen tödlich — nach `requestId`
deduplizieren.

## Werkzeuge einzeln

| Werkzeug | n | p25 | Median | Mittel | p90 | max |
|---|---:|---:|---:|---:|---:|---:|
| Bash | 7.348 | 109 | 234 | 663 | 1.325 | 41.223 |
| Read (eine Datei) | 1.078 | 769 | 1.759 | 3.273 | 8.342 | 30.999 |
| Read je 100 Zeilen | 602 | 2.156 | 2.534 | 3.587 | — | — |
| Edit | 1.433 | 71 | 87 | 160 | 125 | 34.710 |
| Write | 514 | 76 | 91 | 282 | 196 | 17.082 |
| Grep | 44 | 99 | 168 | 380 | 683 | 3.413 |
| WebSearch | 26 | 999 | 1.201 | 1.717 | 1.670 | 12.105 |
| WebFetch | 16 | 239 | 452 | 383 | 539 | 582 |
| playwright browser_snapshot | 85 | 728 | 1.321 | 1.995 | 4.015 | 12.714 |
| playwright browser_click | 227 | 175 | 221 | 301 | 460 | 2.628 |
| playwright browser_evaluate | 401 | 285 | 493 | 764 | 1.562 | 20.336 |
| Bild (Screenshot / Read PNG) | 493 | — | 1.744 | 1.543 | 2.969 | 6.597 |
| supabase execute_sql | 204 | 312 | 419 | 852 | 1.581 | 11.704 |
| ToolSearch | 281 | 593 | 929 | 1.391 | 3.007 | 14.867 |
| ExitPlanMode | 73 | 4.961 | 7.557 | 8.425 | 12.706 | 36.627 |
| AskUserQuestion | 137 | 292 | 450 | 5.445 | 19.524 | 52.929 |
| **Agent — Abschlussbericht** | 18 | 385 | **398** | 522 | 424 | 2.576 |
| **Workflow — Fan-out-Bericht** | 51 | 658 | **702** | 892 | 828 | 8.008 |
| **TaskOutput** ⚠️ | 15 | 89 | 91 | **8.494** | 21.839 | 50.560 |

Dünne Stichprobe (Median belastbar, p90 nicht): Glob (7), WebFetch (16), Agent (18), WebSearch (26).

## Faustformel

**Kontextzuwachs ≈ Zeichen der Werkzeugausgabe geteilt durch 2** — über alle Größenklassen
stabil (1,56 bei <500 Zeichen bis 2,04 bei 30–100k). Unabhängig gegengeprüft: Plandateien-Median
14.759 Zeichen ↔ ExitPlanMode-Median 7.557 Token = Faktor 1,95.

⚠️ `tokens(text) = len(text) // 4` 
**unterschätzt den echten Zuwachs um Faktor 2.** Grund: Code mit Zeilennummern, Logs und JSON
liegen bei ~2–3 Zeichen je Token, dazu Fixkosten je Werkzeugantwort (219 Token bei Bash,
318 bei Read, 70 bei Edit).

## Subagenten-Hebel

| Größe | Wert |
|---|---|
| Interner Spitzenkontext, Median | 111.854 |
| Mittel / p90 / max | 117.114 / 172.133 / 288.112 |
| Anteil über 100k intern | 61 % |
| Im Hauptthread sichtbar | 398–702 Token |
| **Hebel** | **160 : 1** |

## Woher der Kontext großer Sessions kommt

179 Sessions > 200 KB, 38,51 Mio Token Zuwachs:

| Quelle | Anteil |
|---|---:|
| Modellausgabe (Text + Denken + Werkzeugaufrufe) | **46,5 %** |
| Bash | 17,7 % |
| Read | 16,5 % |
| AskUserQuestion | 2,0 % |
| ExitPlanMode | 1,6 % |
| ToolSearch | 1,2 % |

## Startballast und Wiederanlauf

222 Opus-5-Sessions seit 24.08.2026, erste Assistant-Antwort abzüglich der ersten Nutzernachricht:

| | Token |
|---|---:|
| p10 / p25 | 33.829 / 42.668 |
| **Median** | **54.735** |
| p75 / p90 | 64.899 / 71.417 |
| Arbeitsverzeichnis `~/` (volle MCP-Ausstattung, n=153) | 57.039 |
| Scratchpad, weniger MCP (n=57) | 33.876 |

⚠️ Die Spanne ist kein Rauschen, sondern die **MCP-Ausstattung**: 23k Unterschied. Ein
MCP-Server, den die Etappe nicht braucht, kostet vor dem ersten Wort.

Wiederanlauf aus einem Handoff (20 Sessions): Turn 1 bei 71.601, nach 6 Turns 105.153 —
**Wiederorientierung ~38.215** (p75 49.668). Zusammen mit dem Ballast kostet **jeder Schnitt
rund 110.000 Token.** Das ist die härteste Schranke gegen Über-Fragmentierung.

## Endstände und Schrittkosten

359 Sessions: Median 192.859 · p75 434.595 · p90 570.880 · max 954.743.
Über 600k: 8 % · **über 800k: 3 Sessions (1 %)** — 999.032 (15.08.), 954.743 (01.09.),
851.237 (10.08.) · über 1M: keine.

Zuwachs je API-Schritt (2.444 Messungen): Median 1.297 · Mittel 2.291 · p90 5.173 · max 52.418.
Ein einzelner Sprung von 52k ist der Grund, warum Rot schon bei 850k beginnt: in die letzten
150k bis zum Deckel (seit 22.09.2026 = 1M = Fenster) passen nur noch knapp drei solcher Sprünge.

Zuwachs je Session nach Arbeitsart (≥ 8 Turns):

| Art | n | p25 | Median | p90 | max |
|---|---:|---:|---:|---:|---:|
| Browser-lastig (≥ 15 Playwright-Aufrufe) | 23 | 294.383 | 441.288 | 621.631 | 880.834 |
| Subagenten-lastig | 21 | 287.324 | 370.009 | 601.982 | 702.877 |
| Datei-/Codearbeit | 31 | 242.278 | 331.699 | 498.674 | 590.096 |
| Analyse / Gespräch | 74 | 42.284 | 67.242 | 289.467 | 584.062 |

## Der Auto-Compact-Unfall

15.08.2026, 07:18 Uhr, aus dem Transcript:
`trigger: auto · preTokens: 1.000.513 · postTokens: 20.505 · cumulativeDroppedTokens: 980.008 ·
durationMs: 102.361`

980.008 Token weggeworfen, 102 Sekunden Stillstand, Auswahl allein durch das Modell. Kontext
danach: 71.797. Ein Neustart aus einem Handoff beginnt bei 71.601 — preisgleich. Der Unterschied
ist ausschließlich, wer auswählt.

## Nachmessen

Die Zahlen veralten, sobald sich die MCP-Ausstattung ändert (Startballast) oder neue
Werkzeuge dazukommen. Beim Nachmessen dieselben Filter und dieselbe Deduplizierung verwenden,
sonst sind die Werte nicht vergleichbar. Weicht eine Etappe zweimal in dieselbe Richtung ab,
gehört die reale Zahl hier hinein — nicht in eine zweite Liste.
