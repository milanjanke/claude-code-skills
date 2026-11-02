# Claude Code Skills: Kontext im Griff

Skills und Hooks für [Claude Code](https://docs.claude.com/en/docs/claude-code), mit denen große Aufgaben nicht an der Auto-Kompaktierung scheitern. Die Werte sind **gemessen**, nicht geschätzt: 359 Sessions, 13.145 Werkzeug-Turns.

<sub>🇬🇧 Claude Code skills and hooks for context budgeting: split big plans into stages that fit the context window, measure the real fill level, and hand off cleanly between sessions. Docs are in German; the cost map in `skills/etappenplan/referenzen/kostenkarte.md` is numbers-first.</sub>

## Warum

Eine gemessene Session lief bis `preTokens: 1.000.513`, dann griff die Auto-Kompaktierung: **980.008 Token verworfen, 102 Sekunden Stillstand**, und das Modell hat allein entschieden, was bleibt. Ein Neustart aus einer Übergabedatei kostet gleich viel (71.601 statt 71.797 Token), aber du entscheidest, was mitgeht.

## Inhalt

| Teil | Was er macht |
|---|---|
| [`skills/etappenplan`](skills/etappenplan/SKILL.md) | Schneidet große Pläne in Etappen mit Budgetzeile und Handoff-Punkt. Mit Kostenkarte je Schritt-Typ und Zwei-Seiten-Test |
| [`skills/session-check`](skills/session-check/SKILL.md) | Schreibt eine Übergabedatei mit Start-Prompt für die nächste Session, danach `/clear` |
| [`hooks/plan_etappen_gate.py`](hooks/plan_etappen_gate.py) | Blockt `ExitPlanMode`, wenn ein großer Plan keine Etappen hat. Höchstens 2× je Session, fällt im Zweifel offen aus |
| [`hooks/kontext_ampel.py`](hooks/kontext_ampel.py) | Liest den echten Füllstand aus dem Transcript und meldet ihn dem Modell ab 65 % |
| [`hooks/statusline_kontext.sh`](hooks/statusline_kontext.sh) | Statuszeile: `🟢 ctx 193k/1000k · 19% · Rest 807k` |

## Installation

Voraussetzungen: `python3`, `jq`.

```bash
git clone https://github.com/milanjanke/claude-code-skills.git
cd claude-code-skills
mkdir -p ~/.claude/skills ~/.claude/hooks
cp -R skills/* ~/.claude/skills/
cp hooks/* ~/.claude/hooks/ && chmod +x ~/.claude/hooks/*
```

Dann die Einträge aus [`settings.example.json`](settings.example.json) in `~/.claude/settings.json` übernehmen.

**Kleineres Fenster als 1M?** `export KONTEXT_DECKEL=200000` (z. B. in `~/.zshrc`). Alle Schwellen gelten anteilig: Gelb 65 %, Rot 85 %.

## Rauchtest

Nach der Installation und nach jedem Claude-Code-Update:

```bash
# Großer Plan ohne Etappen → muss blocken (exit 2)
echo '{"tool_name":"ExitPlanMode","session_id":"rauchtest-'$RANDOM'","tool_input":{"plan":"Umbau, geschätzt 900k"}}' \
  | python3 ~/.claude/hooks/plan_etappen_gate.py; echo "exit=$?"

# Geschnittener Plan → muss durchlassen (exit 0)
printf '%s' '{"tool_name":"ExitPlanMode","session_id":"rauchtest-'$RANDOM'","tool_input":{"plan":"## Etappe 1 von 2 — Bau\n- Kontextbudget: ~300k\n- Handoff: session-check\n## Etappe 2 von 2 — Abnahme\n- Kontextbudget: ~200k"}}' \
  | python3 ~/.claude/hooks/plan_etappen_gate.py; echo "exit=$?"
```

## Lizenz

MIT · [Milan Janke](https://github.com/milanjanke) · [DLMJ](https://dlmj.de)
