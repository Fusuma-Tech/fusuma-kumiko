"""El harness: lo que el plugin hace solo, sin que nadie se acuerde.

Claude Code lo llama desde `hooks/hooks.json` en cinco momentos. Cada uno lee
un JSON por stdin y contesta con otro JSON por stdout (o con nada):

    sesion        SessionStart      presenta el cerebro en dos líneas
    prompt        UserPromptSubmit  enruta el prompt y añade las reglas que casan
    tras-editar   PostToolUse       vigila el fichero recién escrito
    antes-de-bash PreToolUse(Bash)  no deja hacer `git commit` con hallazgos que bloquean
    al-parar      Stop              revisa todo lo pendiente antes de dar algo por hecho

La idea completa está en docs/HARNESS.md. Lo importante: hasta ahora el agente
tenía que DECIDIR llamar a `reglas_para_tarea`. Con esto las reglas llegan
igual, aunque no lo haga. Se apaga pieza a pieza desde `kumiko.json` → `harness`.

Sin cerebro en el proyecto no hace nada, salvo decirlo una vez al empezar.
Vale con Python 3.9: no importa `mcp`.

Probarlo a mano:
    echo '{"prompt":"guardo una reserva"}' | python3 motor/harness.py prompt
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from nucleo import Cerebro, Config, localiza  # noqa: E402
import telemetria  # noqa: E402
import vigilar  # noqa: E402


def entrada() -> dict:
    try:
        bruto = sys.stdin.read()
        return json.loads(bruto) if bruto.strip() else {}
    except json.JSONDecodeError:
        return {}


def proyecto_de(e: dict) -> pathlib.Path:
    return pathlib.Path(e.get('cwd') or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()).resolve()


def cerebro_de(proyecto: pathlib.Path):
    try:
        return Cerebro(Config(localiza(str(proyecto))))
    except SystemExit:
        return None


def responde(obj: dict | None) -> int:
    if obj:
        print(json.dumps(obj, ensure_ascii=False))
    return 0


def contexto(evento: str, texto: str) -> dict:
    return {'hookSpecificOutput': {'hookEventName': evento, 'additionalContext': texto}}


def formatea_hallazgos(hs: list[dict], maximo: int = 8) -> str:
    L = []
    for h in hs[:maximo]:
        marca = 'BLOQUEA' if h['bloquea'] else 'aviso'
        L.append('- `%s` %s:%d  [%s]\n  %s\n  → %s' % (h['regla'], h['ruta'], h['linea'], marca, h['texto'][:110], h['mensaje']))
    if len(hs) > maximo:
        L.append('- … y %d más' % (len(hs) - maximo))
    return '\n'.join(L)


# ───────────────────────── los cinco hooks ─────────────────────────

def sesion(e: dict) -> int:
    proyecto = proyecto_de(e)
    c = cerebro_de(proyecto)
    if c is None:
        return responde(contexto('SessionStart',
            'kumiko: este proyecto no tiene cerebro de contexto. Si el usuario quiere uno, la skill '
            'es «inicia un cerebro kumiko aquí». Si no, ignora este aviso.'))
    h = c.cfg.harness
    activos = [n for n, k in (('reglas en cada prompt', 'inyectar_reglas'), ('vigilancia al editar', 'vigilar_al_editar'),
                              ('commit bloqueado con hallazgos', 'bloquear_commit'), ('revisión al terminar', 'revisar_al_parar')) if h[k]]
    comps = len(c.comprobaciones())
    return responde(contexto('SessionStart',
        'kumiko · «%s»: %d reglas en %d ficheros, %d defectos, %d comprobaciones automáticas. '
        'Harness activo: %s. Las reglas que apliquen a cada tarea te llegarán solas; cítalas por id. '
        'Para el texto completo, `regla("<id>")`; antes de dar algo por hecho, `checklist_entrega()`.'
        % (c.cfg.nombre, len(c.reglas), len(c.ficheros), len(c.defectos), comps, ', '.join(activos) or 'ninguno')))


def prompt(e: dict) -> int:
    texto = (e.get('prompt') or e.get('user_message') or e.get('userPrompt') or '').strip()
    proyecto = proyecto_de(e)
    c = cerebro_de(proyecto)
    if c is None or not c.cfg.harness['inyectar_reglas']:
        return 0
    if texto.startswith('/') or len(texto.split()) < c.cfg.harness['minimo_palabras']:
        return 0                       # un comando o un «sí»: no hay nada que enrutar
    aciertos = c.busca(texto, max_ficheros=2)
    ids = [rid for _, _, reglas in aciertos for rid, _ in reglas]
    telemetria.registra(c.cfg, 'hook:prompt', texto, ids)
    if not aciertos:
        return 0
    L = ['kumiko · reglas que aplican a lo que acabas de pedir (cítalas por id; texto completo con `regla("<id>")`):']
    tope = c.cfg.harness['maximo_caracteres']
    for fid, term_fich, reglas in aciertos:
        f = c.ficheros[fid]
        L.append('%s · %s%s' % (fid, f['titulo'], (' _(casa en: %s)_' % ', '.join(term_fich)) if term_fich else ''))
        for rid, _ in reglas[:4]:
            r = c.reglas[rid]
            L.append('  - `%s` %s — %s' % (rid, r['titulo'], r['resumen']))
        if sum(len(x) for x in L) > tope:
            break
    rel = [d for d in c.defectos.values() if d['regla'] in set(ids)]
    if rel:
        L.append('Ya costó caro: ' + ', '.join('`%s` %s' % (d['id'], d['titulo']) for d in rel[:3]))
    salida = '\n'.join(L)
    return responde(contexto('UserPromptSubmit', salida[:tope + 400]))


def tras_editar(e: dict) -> int:
    proyecto = proyecto_de(e)
    c = cerebro_de(proyecto)
    if c is None or not c.cfg.harness['vigilar_al_editar']:
        return 0
    ti = e.get('tool_input') or {}
    ruta = ti.get('file_path') or ti.get('path') or ti.get('notebook_path')
    if not ruta:
        return 0
    hs = vigilar.busca_hallazgos(c, vigilar.lineas_de_ficheros(proyecto, [ruta]))
    if not hs:
        return 0
    telemetria.registra(c.cfg, 'hook:editar', ruta, [h['regla'] for h in hs], bloqueo=any(h['bloquea'] for h in hs))
    return responde({'decision': 'block', 'reason':
        'kumiko · el fichero que acabas de escribir tiene %d sitio(s) que casan con una regla del cerebro. '
        'Cada uno es un lugar donde tienes que poder explicar por qué está bien; si no puedes, corrígelo '
        'antes de seguir:\n%s' % (len(hs), formatea_hallazgos(hs))})


def antes_de_bash(e: dict) -> int:
    cmd = ((e.get('tool_input') or {}).get('command') or '')
    if not re.search(r'\bgit\b.*\bcommit\b', cmd):
        return 0
    proyecto = proyecto_de(e)
    c = cerebro_de(proyecto)
    if c is None or not c.cfg.harness['bloquear_commit']:
        return 0
    try:
        fuentes = vigilar.lineas_del_diff(proyecto, None)          # lo preparado para el commit
    except SystemExit:
        return 0
    hs = [h for h in vigilar.busca_hallazgos(c, fuentes) if h['bloquea']]
    if not hs:
        return 0
    telemetria.registra(c.cfg, 'hook:commit', cmd[:120], [h['regla'] for h in hs], bloqueo=True)
    return responde({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
        'permissionDecisionReason': 'kumiko · el commit lleva %d hallazgo(s) que bloquean. Corrígelos, o si de '
                                    'verdad no aplican, díselo al usuario y que decida él:\n%s' % (len(hs), formatea_hallazgos(hs))}})


def al_parar(e: dict) -> int:
    if e.get('stop_hook_active'):
        return 0                       # ya paramos a Claude una vez: no entrar en bucle
    proyecto = proyecto_de(e)
    c = cerebro_de(proyecto)
    if c is None or not c.cfg.harness['revisar_al_parar']:
        return 0
    hs = [h for h in vigilar.busca_hallazgos(c, vigilar.lineas_de_cambios(proyecto)) if h['bloquea']]
    if not hs:
        return 0
    telemetria.registra(c.cfg, 'hook:parar', '', [h['regla'] for h in hs], bloqueo=True)
    return responde({'decision': 'block', 'reason':
        'kumiko · antes de dar esto por hecho: hay %d sitio(s) en los cambios sin commit que incumplen una '
        'regla con `bloquea: sí`. Corrígelos o explica al usuario por qué no aplican, y termina con '
        '`checklist_entrega()`:\n%s' % (len(hs), formatea_hallazgos(hs))})


ORDENES = {'sesion': sesion, 'prompt': prompt, 'tras-editar': tras_editar,
           'antes-de-bash': antes_de_bash, 'al-parar': al_parar}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ORDENES:
        print('uso: harness.py <%s>  (lee el JSON del hook por stdin)' % '|'.join(ORDENES), file=sys.stderr)
        return 2
    try:
        return ORDENES[sys.argv[1]](entrada())
    except Exception as ex:  # noqa: BLE001 — un hook roto nunca debe romper la sesión
        print('kumiko harness: %s: %s' % (type(ex).__name__, ex), file=sys.stderr)
        return 0


if __name__ == '__main__':
    sys.exit(main())
