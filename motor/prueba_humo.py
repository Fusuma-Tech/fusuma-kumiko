#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba de humo de kumiko. Recorre el ciclo entero sobre un cerebro real.

    python3 motor/prueba_humo.py            # sobre ejemplo/
    python3 motor/prueba_humo.py /mi/cerebro

Comprueba, en este orden:
  1. el generador escribe índice y datos
  2. el comprobador da el cerebro por coherente
  3. el comprobador **detecta** un cerebro roto (si no, no está comprobando nada)
  4. el servidor responde por línea de comandos
  5. el servidor habla MCP de verdad por stdio: initialize, tools/list, tools/call
  6. vigilar encuentra los incumplimientos que las comprobaciones declaran
  7. el visor compila, si tiene las dependencias instaladas

Sale con código 1 si algo falla. Vale para CI.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

MOTOR = pathlib.Path(__file__).resolve().parent
KUMIKO = MOTOR.parent
VERDE, ROJO, GRIS, FIN = '\033[32m', '\033[31m', '\033[90m', '\033[0m'
resultados: list[tuple[bool, str, str]] = []


def paso(ok: bool, nombre: str, detalle: str = '') -> bool:
    resultados.append((ok, nombre, detalle))
    print('  %s %-46s %s%s' % ((VERDE + '✓' + FIN) if ok else (ROJO + '✗' + FIN),
                               nombre, GRIS, detalle + FIN))
    return ok


def corre(args, cwd=None, env=None):
    return subprocess.run([sys.executable, *args], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=120)


def main() -> int:
    cerebro = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else KUMIKO / 'ejemplo'
    print('\nkumiko · prueba de humo sobre %s\n' % cerebro)

    r = corre([str(MOTOR / 'construir_indice.py'), str(cerebro)])
    paso(r.returncode == 0, 'el generador escribe índice y datos',
         r.stdout.strip().split('\n')[0] if r.returncode == 0 else r.stderr.strip()[:120])

    r = corre([str(MOTOR / 'comprobar.py'), str(cerebro)])
    paso(r.returncode == 0, 'el cerebro es coherente', r.stdout.strip().split('\n')[-1][:110])

    # 3. un comprobador que nunca falla no comprueba nada: se le da un cerebro roto
    with tempfile.TemporaryDirectory() as tmp:
        copia = pathlib.Path(tmp) / 'cerebro'
        shutil.copytree(cerebro, copia, ignore=shutil.ignore_patterns('.kumiko'))
        roto = next(iter(sorted((copia / 'reglas').rglob('*.md'))), None)
        if roto:
            roto.write_text(roto.read_text(encoding='utf-8')
                            + '\n## ZZZ-QQQ-1 · Cita algo inexistente\n\nVer `ZZZ-QQQ-9` y `§9999`.\n',
                            encoding='utf-8')
            corre([str(MOTOR / 'construir_indice.py'), str(copia)])
            r = corre([str(MOTOR / 'comprobar.py'), str(copia)])
            paso(r.returncode == 1 and 'inexistente' in r.stdout,
                 'el comprobador detecta un cerebro roto',
                 '%d problemas' % r.stdout.count('\n  '))
        else:
            paso(False, 'el comprobador detecta un cerebro roto', 'no hay reglas que romper')

    r = corre([str(MOTOR / 'servidor_mcp.py'), '--probar', 'guardo un registro y evito duplicados'],
              cwd=str(cerebro))
    ok = r.returncode == 0 and 'Reglas que aplican' in r.stdout
    detalle = '%d caracteres' % len(r.stdout)
    if not ok and r.stderr.strip():
        detalle = 'error: ' + r.stderr.strip().splitlines()[-1]
    paso(ok, 'el servidor responde por consola', detalle)

    paso(*prueba_stdio(cerebro))

    # 6. las comprobaciones se ejecutan de verdad. Sobre el ejemplo, además, tienen
    # que encontrar los defectos plantados en src/: si no, vigilar no vigila.
    comps = corre([str(MOTOR / 'vigilar.py'), '--listar'], cwd=str(cerebro))
    n_comps = int(re.search(r'(\d+) comprobaciones', comps.stdout or '').group(1)) if re.search(r'(\d+) comprobaciones', comps.stdout or '') else 0
    if n_comps == 0:
        print('  %s· %-46s %sel cerebro no declara comprobaciones; salta%s' % (GRIS, 'vigilar encuentra lo que declara', '', FIN))
    else:
        r = corre([str(MOTOR / 'vigilar.py'), '--todo'], cwd=str(cerebro))
        hallazgos = len(re.findall(r'^\s+\S*\x1b\[1m[A-Z][\w-]*-\d+', r.stdout, re.M)) or r.stdout.count('↳ ')
        es_ejemplo = cerebro.resolve() == (KUMIKO / 'ejemplo').resolve()
        ok = (hallazgos >= 3) if es_ejemplo else (r.returncode in (0, 1))
        paso(ok, 'vigilar encuentra lo que declara',
             '%d comprobaciones · %d hallazgos%s' % (n_comps, hallazgos,
                                                     ' (los 3 plantados)' if es_ejemplo and ok else ''))

    visor = KUMIKO / 'visor'
    if (visor / 'node_modules').is_dir():
        env = dict(os.environ, KUMIKO_CEREBRO=str(cerebro))
        r = subprocess.run(['npm', 'run', 'build'], cwd=visor, env=env,
                           capture_output=True, text=True, timeout=600)
        paso(r.returncode == 0, 'el visor compila',
             'páginas generadas' if r.returncode == 0 else r.stderr.strip()[-140:])
    else:
        print('  %s· %-46s %ssin node_modules; salta (cd visor && npm install)%s'
              % (GRIS, 'el visor compila', '', FIN))

    fallos = [n for ok, n, _ in resultados if not ok]
    print()
    if fallos:
        print('%s%d de %d comprobaciones han fallado%s\n' % (ROJO, len(fallos), len(resultados), FIN))
        return 1
    print('%slas %d comprobaciones pasan%s\n' % (VERDE, len(resultados), FIN))
    return 0


def consulta_que_casa(cerebro: pathlib.Path) -> str:
    """Una consulta construida con palabras del propio cerebro.

    Con una frase inventada, `reglas_para_tarea` contestaría "no encuentro nada"
    y la prueba pasaría sin haber recuperado jamás una regla."""
    sys.path.insert(0, str(MOTOR))
    from nucleo import Cerebro, Config  # noqa: PLC0415
    c = Cerebro(Config(cerebro))
    for f in c.ficheros.values():
        if f['aplica_si']:
            return f['aplica_si']
    return next(iter(c.reglas.values()))['titulo'] if c.reglas else 'reglas'


PISTA_MCP = ('hace falta Python >= 3.10 con el paquete mcp · '
             'macOS: brew install python@3.12 && python3.12 -m pip install mcp')


def busca_python() -> tuple[str, str] | None:
    """El intérprete con que Claude Code lanzará el servidor: el mismo criterio que
    motor/lanzar_servidor.sh (>= 3.10 y con `mcp`), empezando por el actual."""
    forzado = os.environ.get('KUMIKO_PYTHON')
    candidatos = [forzado] if forzado else [
        sys.executable, 'python3.13', 'python3.12', 'python3.11', 'python3.10',
        '/opt/homebrew/bin/python3', '/usr/local/bin/python3', 'python3']
    for py in candidatos:
        ruta = shutil.which(py) if py else None
        if not ruta:
            continue
        r = subprocess.run([ruta, '-c', 'import sys, mcp, importlib.metadata as m; '
                            'assert sys.version_info >= (3, 10); print(m.version("mcp"))'],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return ruta, r.stdout.strip()
    return None


def prueba_stdio(cerebro: pathlib.Path) -> tuple[bool, str, str]:
    """Habla MCP de verdad con el servidor: es por donde se rompen los MCP."""
    nombre = 'el servidor habla MCP por stdio'
    encontrado = busca_python()
    if not encontrado:
        return False, nombre, PISTA_MCP
    python, version_mcp = encontrado
    env = dict(os.environ, KUMIKO_CEREBRO=str(cerebro))
    p = subprocess.Popen([python, str(MOTOR / 'servidor_mcp.py')],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=env, text=True, bufsize=1)
    try:
        def envia(m):
            p.stdin.write(json.dumps(m) + '\n')
            p.stdin.flush()

        def lee(t=20):
            fin = time.time() + t
            while time.time() < fin:
                linea = p.stdout.readline()
                if linea.strip():
                    return json.loads(linea)
            return None

        envia({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2024-11-05', 'capabilities': {},
            'clientInfo': {'name': 'prueba_humo', 'version': '0'}}})
        if not (lee() or {}).get('result'):
            return False, nombre, 'sin respuesta al initialize'
        envia({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        envia({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
        tools = [t['name'] for t in (lee() or {}).get('result', {}).get('tools', [])]
        faltan = {'reglas_para_tarea', 'regla', 'defecto', 'checklist_entrega'} - set(tools)
        if faltan:
            return False, nombre, 'faltan herramientas: %s' % ', '.join(sorted(faltan))
        envia({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {
            'name': 'reglas_para_tarea', 'arguments': {'tarea': consulta_que_casa(cerebro)}}})
        txt = ''.join(c.get('text', '') for c in (lee() or {}).get('result', {}).get('content', []))
        if not txt:
            return False, nombre, 'tools/call no devolvió contenido'
        if not re.search(r'`[A-Z]{2,3}(?:-[A-Z]{2,4})?-\d+`', txt):
            return False, nombre, 'la respuesta no trae ninguna regla: %s' % txt.split(chr(10))[0][:70]
        return True, nombre, '%d herramientas · %d caracteres con reglas dentro · mcp %s · %s' % (
            len(tools), len(txt), version_mcp, python if python != sys.executable else 'este python')
    except Exception as e:                                   # noqa: BLE001
        return False, nombre, '%s: %s' % (type(e).__name__, e)
    finally:
        p.terminate()


if __name__ == '__main__':
    sys.exit(main())
