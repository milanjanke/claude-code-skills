#!/bin/bash
# Statuszeile: echter Kontext-Füllstand gegen den Deckel (Standard 1M, KONTEXT_DECKEL setzt ihn).
#
# Eingabe kommt als JSON auf stdin. context_window.total_input_tokens ist bereits
# input_tokens + cache_creation + cache_read — dieselbe Formel wie im Transcript,
# fertig gerechnet. Deshalb KEIN Transcript-Zugriff: das Skript läuft bis zu
# einmal pro Sekunde, nur jq (5 ms), kein Python (33 ms Start).
DECKEL=${KONTEXT_DECKEL:-1000000}
GELB=$(( DECKEL * 65 / 100 )); ROT=$(( DECKEL * 85 / 100 ))

IFS=$'\t' read -r USED FENSTER ORDNER <<<"$(jq -r '
  [ (.context_window.total_input_tokens // 0),
    (.context_window.context_window_size // 0),
    (.workspace.current_dir // "" | split("/") | last) ] | @tsv')"
[ -z "$USED" ] && USED=0
[ -z "$FENSTER" ] && FENSTER=0

REST=$(( DECKEL - USED ))
PCT=$(( USED * 100 / DECKEL ))

if   [ "$USED" -lt "$GELB" ]; then AMPEL="🟢"; TIPP=""
elif [ "$USED" -lt "$ROT" ]; then AMPEL="🟡"; TIPP=" · Etappe zu Ende bringen"
elif [ "$USED" -lt "$DECKEL" ]; then AMPEL="🔴"; TIPP=" · Handoff schreiben, dann /clear"
else                              AMPEL="⛔"; TIPP=" · Deckel erreicht — /clear"
fi

# Fenster kleiner als der Deckel: dann stimmt der Deckel nicht, KONTEXT_DECKEL anpassen.
if [ "$FENSTER" -gt 0 ] && [ "$FENSTER" -lt "$DECKEL" ]; then
  TIPP="$TIPP · ⚠ Fenster nur $((FENSTER/1000))k"
fi

printf '%s ctx %sk/%sk · %s%% · Rest %sk%s%s\n' \
  "$AMPEL" "$((USED/1000))" "$((DECKEL/1000))" "$PCT" "$((REST/1000))" \
  "$TIPP" "${ORDNER:+ · $ORDNER}"
