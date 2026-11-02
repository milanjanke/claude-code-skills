---
name: session-check
description: >-
  Erstellt eine Handoff-Zusammenfassung der aktuellen Session und schreibt sie als Datei, die man in die nächste Session mitnehmen kann — danach /clear. Trigger: "handoff", "zusammenfassung für nächste session", "session zusammenfassen", "schreib eine zusammenfassung", "bevor ich /clear drücke", "session handoff"
---

# Session Handoff

Erstelle eine kompakte Zusammenfassung der aktuellen Session und schreibe sie nach
`$HANDOFF_DIR/[JJJJ-MM-TT]-[thema].md` (ohne gesetzte Variable: `~/.claude/handoffs/`).

## Format

```markdown
# Handoff: [Thema] — [Datum]

## Erreicht
- [Ergebnis 1]
- [Ergebnis 2]

## Noch offen
- [Was aussteht oder geblockt ist]

## Wichtige Entscheidungen / Fakten
- [Entscheidung oder Fakt, den Claude in der nächsten Session kennen muss]
- [Relevante Dateipfade]

## Start-Prompt für nächste Session
"[Fertiger Prompt — direkt kopieren und in neue Session einfügen]"
```

Läuft ein Etappenplan (Skill `etappenplan`): zusätzlich die erledigte Etappe **in der Plandatei**
auf `Stand: erledigt (TT.MM., <Endstand in Token>)` setzen — **ohne Zahl gilt die Etappe als
offen**, und der Start-Prompt nennt Plandatei plus nächste Etappennummer. Die Plandatei ist die
Wahrheit über den Fortschritt — der Handoff verweist auf sie, statt sie zu kopieren.

## Drei Handgriffe, die dazugehören

**1. Vorher messen, nicht erinnern.** Den Umgebungszustand messen und übernehmen: ungesicherte
Dateien je berührtem Repo (`git status --short`), belegte Ports (`lsof -iTCP -sTCP:LISTEN -nP`),
laufende Hintergrundprozesse, offene Browser-Logins. Genau das fehlt sonst in Handoffs, die
später überholt sind.

**2. Ältere Handoffs zum selben Thema überholen.** Liegt im Handoff-Ordner bereits eine Datei zum
selben Vorhaben, deren Stand jetzt falsch ist, bekommt sie **oben** eine Zeile:
`> ⚠️ ÜBERHOLT am TT.MM. durch [neue-datei.md] — <was jetzt anders gemessen wurde>`
Nötig, weil parallele Sessions den alten Stand sonst als aktuell lesen. In 5 von 20 geprüften
Handoffs war genau das der Fall.

**3. Memory-Zeile vorschlagen, nicht heimlich schreiben.** Gab es einen Befund, der über diese
Session hinaus gilt (eine Falle, ein Messwert, eine Entscheidung mit Begründung), dann am Ende
**eine fertige Zeile für `MEMORY.md`** vorschlagen — Titel und ein Satz, höchstens 150 Zeichen,
Details in eine eigene Datei. ⛔ Niemals ein Geheimnis in eine Memory-Datei: Sie wird bei jedem
Sessionstart geladen.

Nicht in den Handoff: Bash-Ausgaben, Dateiinhalte, Suchergebnisse, Screenshots. Alles, was
reproduzierbar ist, bleibt draußen — hinein kommt nur, was teurer wiederzubeschaffen als
hinzuschreiben ist (Entscheidungen mit Begründung, Sackgassen, Umgebungszustand, was gemessen
wurde und was nur behauptet ist).

Danach empfehlen: _Datei gespeichert — jetzt `/clear` drücken und mit dem Start-Prompt neu einsteigen._
