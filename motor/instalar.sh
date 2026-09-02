#!/bin/sh
# Prepara lo único que kumiko necesita instalar: el paquete `mcp` para el servidor.
#
# Lo mete en un entorno virtual propio, ~/.kumiko/venv, sin tocar ningún Python del
# sistema (Homebrew y Debian bloquean `pip install` fuera de un venv, y con razón).
# El lanzador del servidor (lanzar_servidor.sh) y la prueba de humo miran ahí primero.
#
#   sh motor/instalar.sh              usa el primer Python >= 3.10 que encuentre
#   sh motor/instalar.sh python3.12   usa ese intérprete
#   KUMIKO_VENV=/otra/ruta            cambia dónde se crea el entorno

set -e
VENV="${KUMIKO_VENV:-$HOME/.kumiko/venv}"

vale() {
  [ -n "$1" ] && command -v "$1" >/dev/null 2>&1 &&
    "$1" -c 'import sys; assert sys.version_info >= (3, 10)' >/dev/null 2>&1
}

PY="$1"
if [ -n "$PY" ] && ! vale "$PY"; then
  echo "kumiko: $PY no existe o no es Python >= 3.10" >&2; exit 1
fi
if [ -z "$PY" ]; then
  for c in python3.13 python3.12 python3.11 python3.10 \
           /opt/homebrew/bin/python3 /usr/local/bin/python3 python3 python; do
    if vale "$c"; then PY="$c"; break; fi
  done
fi
if [ -z "$PY" ]; then
  cat >&2 <<'MSG'
kumiko: no encuentro ningún Python >= 3.10 (el paquete mcp lo exige).
  macOS:          brew install python@3.12   y vuelve a lanzar este script
  Debian/Ubuntu:  sudo apt install python3.12 python3.12-venv
  Otra ruta:      sh motor/instalar.sh /ruta/a/python3
MSG
  exit 1
fi

echo "kumiko: creando el entorno en $VENV con $("$PY" -c 'import sys; print(sys.version.split()[0])') ($PY)"
"$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip mcp
VERSION=$("$VENV/bin/python" -c 'import importlib.metadata as m; print(m.version("mcp"))')
echo "kumiko: listo · mcp $VERSION en $VENV"
echo "        el servidor lo usará solo; compruébalo con  python3 motor/prueba_humo.py"
