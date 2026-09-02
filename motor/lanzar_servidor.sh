#!/bin/sh
# Arranca el servidor MCP con el primer Python que sirva.
#
# El paquete `mcp` exige Python >= 3.10, y en macOS `python3` a secas suele ser el
# 3.9 de Xcode. Claude Code lanza el servidor sin tu PATH de terminal, así que aquí
# se busca uno válido en los sitios habituales en vez de confiar en `python3`.
#
# Orden de búsqueda: KUMIKO_PYTHON si está definido; el entorno que crea
# motor/instalar.sh (~/.kumiko/venv, o KUMIKO_VENV); y después los Pythons habituales.
#
# Cualquier argumento se pasa tal cual a servidor_mcp.py (la raíz del proyecto).

AQUI=$(cd "$(dirname "$0")" && pwd)
SERVIDOR="$AQUI/servidor_mcp.py"

sirve() {
  # Devuelve 0 si el intérprete existe, es >= 3.10 y tiene el paquete mcp.
  [ -n "$1" ] && command -v "$1" >/dev/null 2>&1 &&
    "$1" -c 'import sys; assert sys.version_info >= (3, 10); import mcp' >/dev/null 2>&1
}

VENV="${KUMIKO_VENV:-$HOME/.kumiko/venv}"
if [ -z "$KUMIKO_PYTHON" ] && sirve "$VENV/bin/python"; then
  exec "$VENV/bin/python" "$SERVIDOR" "$@"
fi

if [ -n "$KUMIKO_PYTHON" ]; then
  if sirve "$KUMIKO_PYTHON"; then exec "$KUMIKO_PYTHON" "$SERVIDOR" "$@"; fi
  echo "kumiko: KUMIKO_PYTHON=$KUMIKO_PYTHON no es un Python >= 3.10 con el paquete mcp" >&2
  exit 1
fi

for py in python3.13 python3.12 python3.11 python3.10 \
          /opt/homebrew/bin/python3 /usr/local/bin/python3 \
          "$HOME/.local/bin/python3" python3 python; do
  if sirve "$py"; then exec "$py" "$SERVIDOR" "$@"; fi
done

cat >&2 <<'MSG'
kumiko: no encuentro un Python >= 3.10 con el paquete `mcp`.
  El servidor MCP lo necesita (los demás scripts del motor valen con 3.9).
  Arréglalo con una orden:   sh /ruta/a/kumiko/motor/instalar.sh
  (crea ~/.kumiko/venv con mcp dentro; en macOS antes: brew install python@3.12)
  Si ya tienes uno en otra ruta:  export KUMIKO_PYTHON=/ruta/a/python3
MSG
exit 1
