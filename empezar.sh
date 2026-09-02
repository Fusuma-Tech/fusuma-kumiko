#!/bin/sh
# kumiko · una sola orden después de clonar.
#
#   sh empezar.sh /ruta/a/tu/proyecto
#   sh empezar.sh                      (el proyecto es la carpeta actual)
#
# Deja el entorno del servidor MCP listo, registra el plugin en Claude Code, abre el
# visor en el navegador y arranca Claude en tu proyecto con la entrevista ya empezada.
# Si el proyecto ya tiene cerebro, Claude arranca enseñándote su mapa.
# Se puede lanzar tantas veces como quieras: lo que ya esté hecho, lo salta.

KUMIKO=$(cd "$(dirname "$0")" && pwd)
PROYECTO=$(cd "${1:-.}" 2>/dev/null && pwd) || { echo "kumiko: no existe la carpeta $1" >&2; exit 1; }

if [ "$PROYECTO" = "$KUMIKO" ]; then
  cat >&2 <<MSG
kumiko: dime en qué proyecto quieres el cerebro; esta carpeta es el propio kumiko.
  sh empezar.sh /ruta/a/tu/proyecto
  (para verlo funcionar sin proyecto:  sh empezar.sh ejemplo)
MSG
  exit 1
fi

paso()  { printf '\n\033[1m%s\033[0m\n' "$1"; }
ok()    { printf '  \033[32m✓\033[0m %s\n' "$1"; }
aviso() { printf '  \033[33m·\033[0m %s\n' "$1"; }

# ── 1. Python con mcp para el servidor ────────────────────────────────────────
paso "1/4 · Servidor MCP"
if (cd "$KUMIKO/ejemplo" && KUMIKO_CEREBRO= sh "$KUMIKO/motor/lanzar_servidor.sh" --probar "x") >/dev/null 2>&1; then
  ok "ya hay un Python con mcp"
else
  sh "$KUMIKO/motor/instalar.sh" || exit 1
fi

# ── 2. El plugin en Claude Code ───────────────────────────────────────────────
paso "2/4 · Plugin en Claude Code"
PLUGIN_DIR=""
if ! command -v claude >/dev/null 2>&1; then
  echo "kumiko: no encuentro el comando 'claude'. Instala Claude Code y repite:" >&2
  echo "  https://code.claude.com/docs/en/quickstart" >&2
  exit 1
fi
if claude plugin list 2>/dev/null | grep -q "kumiko"; then
  ok "kumiko ya está instalado"
else
  claude plugin marketplace add "$KUMIKO" >/dev/null 2>&1 || true
  if claude plugin install kumiko@kumiko --scope user >/dev/null 2>&1 && \
     claude plugin list 2>/dev/null | grep -q "kumiko"; then
    ok "instalado desde $KUMIKO"
  else
    PLUGIN_DIR="--plugin-dir $KUMIKO"
    aviso "no he podido instalarlo de forma permanente; lo cargo solo en esta sesión"
  fi
fi

# ── 3. El visor ───────────────────────────────────────────────────────────────
paso "3/4 · Visor"
VISOR_PID=""
if command -v npm >/dev/null 2>&1; then
  if [ ! -d "$KUMIKO/visor/node_modules" ]; then
    aviso "instalando las dependencias del visor (solo esta vez)…"
    (cd "$KUMIKO/visor" && npm install --silent --no-fund --no-audit) || aviso "npm install ha fallado; sigo sin visor"
  fi
  if [ -d "$KUMIKO/visor/node_modules" ]; then
    mkdir -p "$HOME/.kumiko"
    LOG="$HOME/.kumiko/visor.log"
    PIDF="$HOME/.kumiko/visor.pid"
    # Un visor de una sesión anterior que siguiera vivo se cierra: si no, este
    # arrancaría en otro puerto y verías dos.
    if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
      kill "$(cat "$PIDF")" 2>/dev/null; sleep 1
    fi
    : > "$LOG"
    # El binario directamente, sin npm en medio: así $! es el proceso del visor y se
    # puede cerrar al salir de Claude.
    cd "$KUMIKO/visor" || exit 1
    KUMIKO_CEREBRO="$PROYECTO" ./node_modules/.bin/astro dev --host 127.0.0.1 >"$LOG" 2>&1 &
    VISOR_PID=$!
    echo "$VISOR_PID" > "$PIDF"
    cd "$KUMIKO" || exit 1
    URL=""
    i=0
    while [ $i -lt 40 ]; do
      URL=$(grep -o 'http://127.0.0.1:[0-9]*' "$LOG" 2>/dev/null | head -1)
      if [ -n "$URL" ] && curl -s -o /dev/null "$URL" 2>/dev/null; then break; fi
      sleep 1; i=$((i + 1))
    done
    if [ -n "$URL" ]; then
      ok "visor en $URL (se actualiza solo cuando cambia el cerebro)"
      case "$URL" in *:4321) ;; *) aviso "el puerto 4321 lo ocupa otro proceso (¿un npm run dev anterior?); por eso este" ;; esac
      case "$(uname)" in
        Darwin) open "$URL" ;;
        *) command -v xdg-open >/dev/null 2>&1 && xdg-open "$URL" >/dev/null 2>&1 ;;
      esac
    else
      aviso "el visor no ha arrancado; mira $LOG"
    fi
  fi
else
  aviso "sin node/npm no hay visor; el resto funciona igual (brew install node para tenerlo)"
fi

# ── 4. Claude, ya preguntando ─────────────────────────────────────────────────
paso "4/4 · Claude en $PROYECTO"
if (cd "$PROYECTO" && KUMIKO_CEREBRO= python3 "$KUMIKO/motor/servidor_mcp.py" --probar "x") >/dev/null 2>&1; then
  PROMPT="Este proyecto ya tiene un cerebro kumiko. Llama a la herramienta mapa y resúmemelo en tres líneas: qué cubre, cuántas reglas y defectos tiene, y qué le falta."
  ok "ya hay cerebro: Claude te enseña el mapa"
else
  PROMPT="inicia un cerebro kumiko aquí"
  ok "sin cerebro todavía: Claude empieza la entrevista"
fi
echo
cierra_visor() { [ -n "$VISOR_PID" ] && { pkill -P "$VISOR_PID" 2>/dev/null; kill "$VISOR_PID" 2>/dev/null; rm -f "$PIDF"; }; }
trap cierra_visor EXIT INT TERM
cd "$PROYECTO" && claude $PLUGIN_DIR "$PROMPT"
