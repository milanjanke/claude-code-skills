#!/usr/bin/env python3
"""
Etappen-Gate — PreToolUse-Hook auf ExitPlanMode.

Pläne ohne Etappen-Überschrift laufen durch, solange sie nicht selbst mehr als
DECKEL_K veranschlagen. Hat ein Plan Etappen, müssen sie nummeriert sein und je ein
Kontextbudget nennen. Sonst exit 2 mit Begründung auf stderr: Claude Code blockt den
Tool-Aufruf, zeigt Claude den Text, Claude überarbeitet die Plandatei und ruft
ExitPlanMode erneut auf.

Plantext kommt aus tool_input.plan (Claude Code injiziert ihn vor dem Hook aus
der Plandatei), Rückfall auf tool_input.planFilePath.

Sicherungen gegen Dauerblockade:
  - Subagenten-Pläne (agent_id gesetzt) werden nie geblockt
  - höchstens MAX_BLOCKS Blocks je session_id, danach nur noch Hinweis
  - Kill-Switch: touch ~/.claude/hooks/.etappen-gate-aus
  - jeder unerwartete Zustand -> exit 0 (durchlassen), nie blockieren

NIEMALS permissionDecision "allow" zurückgeben — das überspränge den
Plan-Freigabedialog. Nur exit 2 oder Schweigen.
"""
import json, os, re, sys
from pathlib import Path

BASIS = Path.home() / ".claude"
DECKEL_K = int(os.environ.get("KONTEXT_DECKEL", "1000000")) * 65 // 100 // 1000  # 65 % des Deckels, in k
MAX_BLOCKS = 2      # danach nur noch Hinweis
SKILL = str(BASIS / "skills/etappenplan/SKILL.md")
AUS = BASIS / "hooks/.etappen-gate-aus"
LOGNAME = "etappen"

def log(entscheidung, detail=""):
    """Eine Zeile nach logs/gates.log. Darf niemals werfen — sonst blockiert der Logger das Gate."""
    try:
        import time
        p = BASIS / "logs/gates.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{LOGNAME}\t{entscheidung}\t{detail[:120]}\n")
        if p.stat().st_size > 200_000:          # grob 2000 Zeilen: die Haelfte behalten
            zeilen = p.read_text().splitlines()[-1000:]
            p.write_text("\n".join(zeilen) + "\n")
    except Exception:
        pass

ZAEHLER = BASIS / "hooks/.etappen-gate"

KOPF = re.compile(r"^#{2,3}\s*Etappe\s+(\d+)\b", re.M | re.I)
BUDGET = re.compile(r"^\s*[-*]?\s*Kontextbudget:\s*~?\s*(\d+)\s*k\b", re.M | re.I)
GROSS = re.compile(r"(\d{3,4})\s*k\b", re.I)
# Codeblöcke enthalten Format-Beispiele ("## Etappe 2 von 3 — ...") und dürfen nicht
# als echte Etappen zählen — sonst blockt das Gate jeden Plan, der das Format erklärt.
CODEBLOCK = re.compile(r"^(?:```|~~~).*?(?:^(?:```|~~~)\s*$|\Z)", re.M | re.S)


def ohne_codebloecke(plan):
    return CODEBLOCK.sub("", plan)


def maengel(plan):
    """None = sauber, sonst der erste Mangel im Klartext."""
    plan = ohne_codebloecke(plan)
    treffer = list(KOPF.finditer(plan))
    if not treffer:
        # Kleine Pläne (der Normalfall) brauchen kein Etappenformat. Geblockt wird nur,
        # wenn der Plan selbst mehr als den Deckel veranschlagt.
        gross = [int(z) for z in GROSS.findall(plan) if int(z) > DECKEL_K]
        if not gross:
            return None
        return (f"Plan veranschlagt {max(gross)}k ohne Etappen — erwartet '## Etappe 1 von N — Titel' "
                "mit Zeile '- Kontextbudget: ~NNNk'")
    nummern = [int(t.group(1)) for t in treffer]
    if nummern != list(range(1, len(nummern) + 1)):
        return f"Etappen nicht fortlaufend ab 1 nummeriert: {nummern}"
    grenzen = [t.start() for t in treffer] + [len(plan)]
    for i, nr in enumerate(nummern):
        block = plan[grenzen[i]:grenzen[i + 1]]
        b = BUDGET.search(block)
        if not b:
            return f"Etappe {nr} hat keine Zeile '- Kontextbudget: ~NNNk'"
        k = int(b.group(1))
        if k > DECKEL_K:
            return (f"Etappe {nr} veranschlagt {k}k, erlaubt sind {DECKEL_K}k je Etappe — "
                    f"feiner schneiden oder Lesearbeit an Subagenten delegieren")
        if i < len(nummern) - 1 and "handoff" not in block.lower():
            return f"Etappe {nr} nennt keinen Handoff für den Übergang in die nächste Session"
    return None


def blocks_bisher(session):
    """Zählt Blocks je Session hoch und gibt den Stand VOR diesem Aufruf zurück."""
    name = re.sub(r"[^A-Za-z0-9_-]", "", session or "")[:64] or "unbekannt"
    datei = ZAEHLER / name
    try:
        n = int(datei.read_text())
    except Exception:
        n = 0
    try:
        ZAEHLER.mkdir(parents=True, exist_ok=True)
        datei.write_text(str(n + 1))
    except Exception:
        pass
    return n


def lies(pfad):
    try:
        if pfad and os.path.exists(pfad):
            return Path(pfad).read_text()
    except Exception:
        pass
    return None


def main():
    daten = json.load(sys.stdin)
    if daten.get("tool_name") != "ExitPlanMode" or daten.get("agent_id"):
        return                                   # Subagenten-Pläne nie blocken
    ti = daten.get("tool_input") or {}
    plan = ti.get("plan") or lies(ti.get("planFilePath"))
    if not plan:
        # Kein Plantext, obwohl ExitPlanMode lief: meist hat ein Claude-Code-Update das Feld
        # umbenannt. Ab hier prueft das Gate nichts mehr — deshalb wird genau das protokolliert.
        log("kein-plantext", "Felder: " + ",".join(sorted(ti)))
        return
    mangel = maengel(plan)
    if not mangel:
        log("ok")
        return
    text = (f"Etappen-Gate: {mangel}. Pläne über {DECKEL_K}k werden in Etappen von höchstens "
            f"{DECKEL_K}k geplantem Kontext geschnitten. Format, Kostenkarte und Beispiel: {SKILL}")
    if AUS.exists() or blocks_bisher(daten.get("session_id", "")) >= MAX_BLOCKS:
        log("hinweis", mangel)
        print(json.dumps({"systemMessage": text + " (nur Hinweis, nicht blockiert)"}))
        return
    log("block", mangel)
    print(text + " Überarbeite die Plandatei und rufe ExitPlanMode erneut auf.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        log("fehler", type(e).__name__ + ": " + str(e))
    sys.exit(0)
