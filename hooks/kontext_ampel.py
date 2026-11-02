#!/usr/bin/env python3
"""
Kontext-Ampel — UserPromptSubmit-Hook.

Misst den echten Füllstand aus dem Transcript und gibt ab Gelb eine Zeile auf
stdout aus; Claude Code hängt sie an den Prompt, damit das Modell selbst weiss,
wann es die Etappe schliessen muss. Die Statuszeile sieht nur der Mensch — deshalb
braucht das Modell dieses zweite Signal.

Unter GELB: keine Ausgabe, keine Token-Kosten.

Formel: input_tokens + cache_creation_input_tokens + cache_read_input_tokens
der letzten echten Assistant-Zeile. Filter, jeder einzeln nötig:
  type == "assistant"        (nur die tragen usage)
  isSidechain is not True    (Subagenten nicht mitzählen)
  model != "<synthetic>"     (solche Zeilen haben usage mit lauter Nullen)

Fällt immer offen aus: jeder Fehler -> exit 0 ohne Ausgabe.
"""
import json, os, sys

DECKEL = int(os.environ.get("KONTEXT_DECKEL", "1000000"))
GELB = DECKEL * 65 // 100
ROT = DECKEL * 85 // 100
TAIL = 2_000_000          # nur das Dateiende lesen; Transcripts werden zig MB gross
HANDOFFS = os.environ.get("HANDOFF_DIR", "~/.claude/handoffs/")


def fuellstand(pfad):
    groesse = os.path.getsize(pfad)
    with open(pfad, "rb") as f:
        f.seek(max(0, groesse - TAIL))
        roh = f.read()
    zeilen = roh.split(b"\n")
    if groesse > TAIL:
        zeilen = zeilen[1:]                      # erste Zeile ist angeschnitten
    for zeile in reversed(zeilen):
        if b'"usage"' not in zeile:
            continue
        try:
            o = json.loads(zeile)
        except Exception:
            continue
        if o.get("type") != "assistant" or o.get("isSidechain") is True:
            continue
        m = o.get("message") or {}
        if m.get("model") == "<synthetic>":
            continue
        u = m.get("usage")
        if not u:
            continue
        return (u.get("input_tokens", 0)
                + u.get("cache_creation_input_tokens", 0)
                + u.get("cache_read_input_tokens", 0))
    return None


def main():
    daten = json.load(sys.stdin)
    pfad = daten.get("transcript_path") or ""
    if not pfad or not os.path.exists(pfad):
        return
    ctx = fuellstand(pfad)
    if ctx is None or ctx < GELB:
        return
    kopf = f"[Kontext gemessen: {ctx // 1000}k von {DECKEL // 1000}k, noch {(DECKEL - ctx) // 1000}k."
    if ctx < ROT:
        print(f"{kopf} Gelb: laufende Etappe zu Ende bringen, keine neue anfangen, "
              f"keine neuen Erkundungen. Lesearbeit nur noch über Subagenten.]")
    else:
        print(f"{kopf} Rot: jetzt Handoff nach {HANDOFFS} schreiben (Skill session-check) "
              f"und /clear vorschlagen. Keine neue Etappe in dieser Session.]")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
