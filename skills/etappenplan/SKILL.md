---
name: etappenplan
description: >-
  Schneidet große Pläne in Etappen, die einzeln in den Kontextdeckel passen — mit gemessener
  Kostenkarte, Budgetzeile je Etappe und festem Handoff-Punkt (session-check → /clear →
  nächste Etappe). Nutzen, wenn ein Plan voraussichtlich über 65 % des Deckels braucht, wenn
  Etappen gewünscht sind ("/etappenplan", "in Etappen aufteilen", "das passt nicht in eine
  Session", "wo stehen wir im Plan") oder wenn eine Etappe fertig bzw. ihr Budget gerissen ist.
  Kleine Pläne brauchen ihn nicht.
---

# /etappenplan — Pläne, die ins Kontextfenster passen

Der **Deckel** ist die Kontextmenge, bis zu der eine Session laufen darf. Standard:
**1.000.000 Token** (volles 1M-Fenster). Wer mit einem kleineren Fenster arbeitet, setzt
`KONTEXT_DECKEL` (z. B. `200000`); alle Schwellen gelten dann anteilig.

| Schwelle | Anteil | bei 1M |
|---|---:|---:|
| Gelb | 65 % | 650k |
| Rot | 85 % | 850k |

⚠️ **Warum es den Deckel gibt:** In einer gemessenen Session schlug die automatische
Kompaktierung zu — `preTokens: 1.000.513` → `postTokens: 20.505`. **980.008 Token weggeworfen,
102 Sekunden Stillstand, und das Modell hat allein ausgewählt, was bleibt.** Ein Neustart aus
einem Handoff beginnt bei 71.601 Token, die Auto-Kompaktierung endete bei 71.797. Preisgleich.
Der einzige Unterschied ist, wer auswählt.

**Das Gate** (`hooks/plan_etappen_gate.py`) prüft jeden Plan bei `ExitPlanMode`: Ein Plan ohne
Etappen, der selbst mehr als 65 % des Deckels veranschlagt, wird geblockt; ein Plan mit Etappen
muss das Format unten einhalten. Es blockt **höchstens zweimal je Session** und fällt bei jedem
unerwarteten Zustand offen aus (Protokoll: `~/.claude/logs/gates.log`). Ein durchgekommener
Plan ist also kein Beweis, dass er geschnitten ist — der Beweis steht im Log.

---

## ⛔ Untergrenze: unter 65 % wird NICHT geschnitten

Gemessen über 359 Sessions (1M-Fenster): Median-Endstand **192.859**, p90 **570.880**, nur
**3 Sessions (1 %)** über 800k, **keine einzige über 1M**. Ein Schnitt kostet dagegen **~110k**
(55k Startballast + ~40k Wiederorientierung + Handoff schreiben).

Bleibt der Zwei-Seiten-Test unter 65 %, steht im Plan genau das:

```markdown
## Etappe 1 von 1 — <Titel>
- Kontextbudget: ~180k (typisch) · Reserve p90: ~340k
```

Zwei Zeilen, fertig. **Schneiden ohne Not macht die Arbeit teurer, nicht sicherer.**

---

## Was ein Schritt kostet

Gemessen an 13.145 Werkzeug-Turns und 950 Arbeitsblöcken (Verfahren und Stichproben:
`referenzen/kostenkarte.md`). Eigene Werte verdrängen diese, sobald sie gemessen sind.

| Schritt-Typ | typisch | p90 |
|---|---:|---:|
| Gespräch / Entscheidung / Zwischenbericht | 5k | 25k |
| Datei-/Codeschritt (lesen, ändern, testen) | 20k | 80k |
| Recherche im Web | 15k | 60k |
| **Browser-Vorgang** (ein Anbieter, ein Vorgang) | **85k** | **225k** |
| Subagenten-Fan-out, sauber (nur Bericht zurück) | 3k je Agent | 8k je Agent |
| Fan-out **mit** Nacharbeit im Hauptthread | 45k | 190k |
| Verifikationslauf (Smoke, Messung, Test) | 10k | 40k |
| Bild / Screenshot ansehen | 1,8k | 3k |
| Plan in den Kontext holen (ExitPlanMode) | 7,5k | 12,7k |
| Startballast (System + CLAUDE.md + MCP-Schemas) | 55k | 71k |

### Zwei-Seiten-Test — so entsteht die Budgetzahl

> **Budget = 55k + Σ „typisch"** → muss **≤ 65 % des Deckels** sein.
> **Reserve = 71k + Σ „p90"** → muss **≤ Deckel** sein (71k, weil der Startballast selbst
> einen p90 hat).
> Reißt einer der beiden, wird geschnitten — auch wenn der andere hält.

Bei 1M: Vier Browser-Vorgänge ergeben 395k / 971k → hält knapp. Fünf: 480k / **1.196k** →
schneiden, obwohl Seite A locker passt.

---

## Die drei Hebel — in dieser Reihenfolge

**1. Lesen delegieren. Hebel 160:1.** Ein Subagent verbrennt intern im Median **111.854** Token
und hinterlässt im Hauptthread **398–702**. Ab ~15 zu lesenden Dateien: delegieren, nicht
schneiden. Das ist oft der Unterschied zwischen drei Etappen und einer.
⛔ **Nie `TaskOutput` im Hauptthread lesen** — der Bericht *ist* die Ausgabe. TaskOutput kostet
im Mittel 8.494, p90 21.839, max 50.560 und zerstört den ganzen Hebel.

**2. Ausgaben an der Quelle kappen.** `| tail -50`, `--quiet`, `2>&1 | tail -30`. Bash ist mit
17,7 % die größte Werkzeugposition; der teuerste gemessene Einzelaufruf lag bei 41k.

**3. Kurz antworten.** Die eigene Modellausgabe ist mit **46,5 %** die größte Einzelposition im
Kontext großer Sessions — größer als Bash (17,7 %) und Read (16,5 %) zusammen.

---

## Etappen-Format (genau das prüft das Gate)

```markdown
## Etappe 2 von 3 — Sektionen bauen
- Kontextbudget: ~340k (typisch) · Reserve p90: ~610k
- Ziel: alle 8 Sektionen stehen lokal, Smoke grün
- Enthält: S4, S5, S6
- Abnahme: `npm run build` grün · 8/8 Sektionen in index.html · Screenshot je Sektion
- Handoff: session-check → /clear → „Weiter mit Etappe 3 aus <plandatei>"
```

1. Überschrift `## Etappe N`, fortlaufend ab 1.
2. Je Etappe eine Zeile `- Kontextbudget: ~NNNk`, höchstens 65 % des Deckels (650 bei 1M).
3. Jede Etappe außer der letzten nennt einen **Handoff**.
4. Subagenten-Pläne werden nie geblockt.
5. **Inhalt in ``` oder ~~~ zählt nicht.** Das Gate schneidet Codeblöcke vorher weg. Etappen
   gehören als normaler Text in die Plandatei, nicht in einen Codeblock.

### Wo die Schnittkante liegen darf

Auf einem Abnahmepunkt — nie mitten in Bau, Fan-out, Render oder Iterationsschleife. Alle vier
Bedingungen müssen halten:

1. **Ablesbar.** Ein `ls` plus eine Datei lesen genügt, um zu wissen, wo man steht.
2. **Gemessen.** Die Etappe endet mit einer Messung **am Artefakt** (Dateiliste, Prüfsumme je
   Datei, `ffprobe`) — nicht mit einem Statuscode. Ein SPA-Catch-all antwortet 200 auch für
   fehlende Dateien, und ein CDN-Edge cacht trotz `no-store`.
3. **Kein offener Vorgang.** Kein halbes Formular, kein laufender Render, keine DNS-Änderung
   ohne Propagationsprüfung, keine offene Iterationsschleife.
4. **Kein Kopfwissen.** „Was weiß ich, das in keiner Datei steht?" muss leer sein — oder
   vollständig im Handoff.

Natürliche Grenzen nach Auftragsart: Website = Recherche → Grundgerüst → Sektionen →
Kritik → Deploy · Video = Analyse → Schnittplan → Bau → Render · Audit = Erhebung →
Gegenprüfung → Bericht · **Anbieter-Oberflächen = eine Etappe je Anbieter.**
Muster: Die Grenze liegt dort, wo ein Artefakt entsteht, das die nächste Etappe als Eingabe
liest. Gibt es keins, muss erst eins geschrieben werden.

⚠️ **Die sieben Schnittfehler:** halber Zustand ohne Test · Recherche ohne schriftlichen Befund
(die nächste Etappe recherchiert dasselbe) · Wissen nur im Gespräch statt im Artefakt ·
Sackgassen nicht notiert (teuerster Einzelfehler) · Umgebungszustand vergessen (Logins, Ports,
Branch) · Schnitt mitten in einer Iterationsschleife · zu fein geschnitten.

---

## Zur Laufzeit

Der Stand wird **gemessen, nicht geschätzt**: Die Statuszeile (`hooks/statusline_kontext.sh`)
zeigt ihn dauerhaft, ab Gelb meldet sich die Ampel (`hooks/kontext_ampel.py`) im Prompt.
`/context` ist der Zweitweg.

| Stand | Was gilt |
|---|---|
| 🟢 < 65 % | normal arbeiten |
| 🟡 65–85 % | laufende Etappe zu Ende bringen, keine neue anfangen, keine neuen Erkundungen, Lesearbeit nur über Subagenten |
| 🔴 85–100 % | nur noch abschließen und messen, Handoff schreiben, `/clear` vorschlagen |
| ⛔ ≥ Deckel | nur noch Handoff — auch mitten im Schritt |

**Vorwärtsprüfung, wichtiger als die Ampel:** Reststrecke = Deckel − Stand − 60k
Abschlussreserve. Kein Schritt wird begonnen, dessen **p90** nicht in die Reststrecke passt. Ein
Browser-Vorgang braucht 225k freie Bahn — bei 1M ist er ab 715k unzulässig, obwohl die Ampel bis
850k nur Gelb zeigt.

- Den Handoff-Entwurf **mitlaufend** nach jedem fertigen Schritt schreiben, nicht am Ende.
  Sessions sterben unangekündigt (gemessen: Wochenlimit mitten in einem 124-Agenten-Fan-out).
- Wer eine Etappe fertig meldet, **nennt den Endstand in Token**. Ohne Zahl gilt sie als offen.
- Die erledigte Etappe **in der Plandatei** abhaken. Die Plandatei ist die Wahrheit über den
  Fortschritt; der Handoff verweist auf sie und kopiert sie nicht.
- Reißt eine Etappe ihr Budget zweimal, war die Schätzung falsch: Restetappen **neu schneiden**
  und die reale Zahl in `referenzen/kostenkarte.md` nachtragen.

⚠️ **`/compact` ist die Notbremse, nicht das Verfahren.** Es glättet genau die
Werkzeugausgaben, aus denen die Messwerte stammen, und wieder wählt das Modell aus. Nur bei
laufender Fehlersuche, deren Hypothesenkette der eigentliche Wert ist — und **nie ohne
`Keep:`-Liste**. Sonst: Handoff und `/clear`.

---

## Was in den Handoff gehört

Aufnahmetest: **Nur was teurer wiederzubeschaffen ist als hinzuschreiben.** Deckel 8.000 Zeichen.

**Bleibt drin:** Entscheidungen mit Begründung · Sackgassen mit Grund und Datum ·
Umgebungszustand (Logins, Ports, Branch + SHA) · was gemessen wurde und was nur behauptet ist ·
bewusste Abweichungen vom Standard.

**Muss raus:** Bash-Ausgaben und Logs (17,7 % des Kontexts, reproduzierbar) · Dateiinhalte
und Codeauszüge (16,5 %, die Datei liegt auf der Platte) · Grep-Treffer · Rohtext aus
Websuchen · Screenshots (der Befund bleibt) · Zwischenversionen (Git kennt sie) · der Plan
selbst (wird verlinkt, spart ~7.500 Token).

Geschrieben wird er vom Skill `session-check`.

---

## Dateien

| Datei | Zweck |
|---|---|
| `referenzen/kostenkarte.md` | die Messwerte mit Stichprobe und Verfahren |
| `~/.claude/hooks/plan_etappen_gate.py` | Gate auf ExitPlanMode — blockt Pläne ohne Etappen |
| `~/.claude/hooks/kontext_ampel.py` | meldet dem Modell ab Gelb den gemessenen Stand |
| `~/.claude/hooks/statusline_kontext.sh` | Statuszeile für den Menschen |
| `~/.claude/hooks/.etappen-gate-aus` | Kill-Switch: `touch` schaltet das Gate still |

⚠️ **Nach jedem Claude-Code-Update** den Rauchtest aus dem README wiederholen (ein Plan ohne
Etappen über dem Deckel muss `exit 2` liefern). Bleibt er aus, hat sich die Hook-Schnittstelle
bewegt — das Gate lässt dann still durch und prüft nichts mehr.
