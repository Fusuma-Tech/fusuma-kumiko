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
  6. el servidor arranca en una carpeta sin cerebro y dice cómo crearlo
  7. vigilar encuentra los incumplimientos que las comprobaciones declaran
  8. el harness (los cinco hooks) enruta, vigila y para sobre una copia con un fallo plantado
  9. el enrutado pasa su conjunto de evaluación
 10. el visor compila, si tiene las dependencias instaladas

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
    print('  %s %-52s %s%s' % ((VERDE + '✓' + FIN) if ok else (ROJO + '✗' + FIN),
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
    paso(*prueba_sin_cerebro())

    # 6. las comprobaciones se ejecutan de verdad. Sobre el ejemplo, además, tienen
    # que encontrar los defectos plantados en src/: si no, vigilar no vigila.
    comps = corre([str(MOTOR / 'vigilar.py'), '--listar'], cwd=str(cerebro))
    n_comps = int(re.search(r'(\d+) comprobaciones', comps.stdout or '').group(1)) if re.search(r'(\d+) comprobaciones', comps.stdout or '') else 0
    if n_comps == 0:
        print('  %s· %-52s %sel cerebro no declara comprobaciones; salta%s' % (GRIS, 'vigilar encuentra lo que declara', '', FIN))
    else:
        r = corre([str(MOTOR / 'vigilar.py'), '--todo'], cwd=str(cerebro))
        hallazgos = len(re.findall(r'^\s+\S*\x1b\[1m[A-Z][\w-]*-\d+', r.stdout, re.M)) or r.stdout.count('↳ ')
        es_ejemplo = cerebro.resolve() == (KUMIKO / 'ejemplo').resolve()
        ok = (hallazgos >= 3) if es_ejemplo else (r.returncode in (0, 1))
        paso(ok, 'vigilar encuentra lo que declara',
             '%d comprobaciones · %d hallazgos%s' % (n_comps, hallazgos,
                                                     ' (los 3 plantados)' if es_ejemplo and ok else ''))

    paso(*prueba_harness(cerebro))
    paso(*prueba_evaluacion(cerebro))

    visor = KUMIKO / 'visor'
    if (visor / 'node_modules').is_dir():
        env = dict(os.environ, KUMIKO_CEREBRO=str(cerebro))
        r = subprocess.run(['npm', 'run', 'build'], cwd=visor, env=env,
                           capture_output=True, text=True, timeout=600)
        paso(r.returncode == 0, 'el visor compila',
             'páginas generadas' if r.returncode == 0 else r.stderr.strip()[-140:])
    else:
        print('  %s· %-52s %ssin node_modules; salta (cd visor && npm install)%s'
              % (GRIS, 'el visor compila', '', FIN))

    fallos = [n for ok, n, _ in resultados if not ok]
    print()
    if fallos:
        print('%s%d de %d comprobaciones han fallado%s\n' % (ROJO, len(fallos), len(resultados), FIN))
        return 1
    print('%slas %d comprobaciones pasan%s\n' % (VERDE, len(resultados), FIN))
    return 0


def hook(orden: str, entrada: dict, cwd: str) -> dict:
    """Llama a un hook como lo haría Claude Code: JSON por stdin, JSON por stdout."""
    r = subprocess.run([sys.executable, str(MOTOR / 'harness.py'), orden], input=json.dumps(entrada),
                       capture_output=True, text=True, cwd=cwd, timeout=60)
    if r.returncode != 0:
        raise RuntimeError('%s salió con %d: %s' % (orden, r.returncode, r.stderr.strip()[-160:]))
    return json.loads(r.stdout) if r.stdout.strip() else {}


def prueba_harness(cerebro: pathlib.Path) -> tuple[bool, str, str]:
    """Los cinco hooks, sobre una copia del cerebro con git y un fichero plantado:
    el prompt recibe reglas, el fichero editado da hallazgos, el commit se
    deniega, la parada se bloquea, y con stop_hook_active no hay bucle."""
    nombre = 'el harness enruta, vigila y para'
    if not (cerebro / 'src').is_dir():
        return True, nombre, 'sin src/ en este cerebro; solo se prueba el prompt'
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='kumiko-harness-'))
    try:
        copia = tmp / 'proyecto'
        shutil.copytree(cerebro, copia, ignore=shutil.ignore_patterns('.kumiko', 'node_modules', '.git'))
        cwd = str(copia)
        subprocess.run(['git', 'init', '-q'], cwd=cwd, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=cwd, check=True)
        subprocess.run(['git', '-c', 'user.name=k', '-c', 'user.email=k@k', 'commit', '-q', '-m', 'base'], cwd=cwd, check=True)
        # 1. sesión
        s1 = hook('sesion', {'cwd': cwd}, cwd)
        if 'reglas' not in s1.get('hookSpecificOutput', {}).get('additionalContext', ''):
            return False, nombre, 'SessionStart no presenta el cerebro'
        # 2. prompt → reglas
        s2 = hook('prompt', {'cwd': cwd, 'prompt': consulta_que_casa(cerebro)}, cwd)
        ctx = s2.get('hookSpecificOutput', {}).get('additionalContext', '')
        if not re.search(r'`[A-Z]{2,3}(?:-[A-Z]{2,4})?-\d+`', ctx):
            return False, nombre, 'UserPromptSubmit no inyecta ninguna regla'
        if hook('prompt', {'cwd': cwd, 'prompt': 'sí'}, cwd):
            return False, nombre, 'UserPromptSubmit responde a un prompt de una palabra'
        # 3. un fichero nuevo con un incumplimiento que bloquea
        malo = copia / 'src' / 'Plantado.kt'
        malo.write_text('fun f() {\n  repo.buscarPor(x).onFailure { logger.error("x") }\n}\n', encoding='utf-8')
        s3 = hook('tras-editar', {'cwd': cwd, 'tool_name': 'Write', 'tool_input': {'file_path': str(malo)}}, cwd)
        if s3.get('decision') != 'block':
            return False, nombre, 'PostToolUse no devuelve el hallazgo del fichero editado'
        # 4. commit denegado
        subprocess.run(['git', 'add', '-A'], cwd=cwd, check=True)
        s4 = hook('antes-de-bash', {'cwd': cwd, 'tool_name': 'Bash', 'tool_input': {'command': 'git commit -m "x"'}}, cwd)
        if s4.get('hookSpecificOutput', {}).get('permissionDecision') != 'deny':
            return False, nombre, 'PreToolUse deja pasar un commit con hallazgos que bloquean'
        if hook('antes-de-bash', {'cwd': cwd, 'tool_name': 'Bash', 'tool_input': {'command': 'ls -la'}}, cwd):
            return False, nombre, 'PreToolUse se mete con un comando que no es commit'
        # 5. parada bloqueada, y sin bucle
        s5 = hook('al-parar', {'cwd': cwd, 'stop_hook_active': False}, cwd)
        if s5.get('decision') != 'block':
            return False, nombre, 'Stop deja terminar con hallazgos que bloquean'
        if hook('al-parar', {'cwd': cwd, 'stop_hook_active': True}, cwd):
            return False, nombre, 'Stop vuelve a bloquear con stop_hook_active: bucle'
        tel = copia / '.kumiko' / 'consultas.jsonl'
        n = len(tel.read_text(encoding='utf-8').strip().split('\n')) if tel.exists() else 0
        return True, nombre, '5 hooks · prompt con reglas · edición, commit y parada bloqueados · %d eventos en telemetría' % n
    except Exception as e:  # noqa: BLE001
        return False, nombre, '%s: %s' % (type(e).__name__, e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def prueba_evaluacion(cerebro: pathlib.Path) -> tuple[bool, str, str]:
    nombre = 'el enrutado pasa su evaluación'
    r = corre([str(MOTOR / 'evaluar.py'), '--json', str(cerebro)])
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return False, nombre, (r.stderr.strip() or r.stdout.strip())[-140:]
    if not d['casos']:
        return True, nombre, 'sin conjunto de evaluación (%s); salta' % d['fichero']
    return bool(d['pasa']), nombre, 'recall %.0f%% · precisión %.0f%% · %d de %d consultas bien' % (
        d['recall'] * 100, d['precision'] * 100, d['ok'], d['casos'])


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


PISTA_MCP = 'hace falta Python >= 3.10 con el paquete mcp · lanza:  sh motor/instalar.sh'


def busca_python() -> tuple[str, str] | None:
    """El intérprete con que Claude Code lanzará el servidor: el mismo criterio que
    motor/lanzar_servidor.sh (>= 3.10 y con `mcp`), empezando por el actual."""
    forzado = os.environ.get('KUMIKO_PYTHON')
    venv = pathlib.Path(os.environ.get('KUMIKO_VENV') or pathlib.Path.home() / '.kumiko' / 'venv')
    candidatos = [forzado] if forzado else [
        str(venv / 'bin' / 'python'), str(venv / 'Scripts' / 'python.exe'),
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


class Sesion:
    """Una conversación MCP por stdio con el servidor, lo justo para probarlo."""

    def __init__(self, python: str, cwd=None, env=None):
        self.p = subprocess.Popen([python, str(MOTOR / 'servidor_mcp.py')], cwd=cwd,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env=env, text=True, bufsize=1)
        self.n = 0

    def envia(self, m):
        self.p.stdin.write(json.dumps(m) + '\n')
        self.p.stdin.flush()

    def lee(self, t=20):
        fin = time.time() + t
        while time.time() < fin:
            linea = self.p.stdout.readline()
            if linea.strip():
                return json.loads(linea)
        return None

    def llama(self, metodo, params=None):
        self.n += 1
        self.envia({'jsonrpc': '2.0', 'id': self.n, 'method': metodo, 'params': params or {}})
        return (self.lee() or {}).get('result', {})

    def herramienta(self, nombre, **argumentos) -> str:
        r = self.llama('tools/call', {'name': nombre, 'arguments': argumentos})
        return ''.join(c.get('text', '') for c in r.get('content', []))

    def abre(self) -> bool:
        ok = bool(self.llama('initialize', {
            'protocolVersion': '2024-11-05', 'capabilities': {},
            'clientInfo': {'name': 'prueba_humo', 'version': '0'}}))
        self.envia({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        return ok

    def cierra(self):
        self.p.terminate()


def prueba_stdio(cerebro: pathlib.Path) -> tuple[bool, str, str]:
    """Habla MCP de verdad con el servidor: es por donde se rompen los MCP."""
    nombre = 'el servidor habla MCP por stdio'
    encontrado = busca_python()
    if not encontrado:
        return False, nombre, PISTA_MCP
    python, version_mcp = encontrado
    s = Sesion(python, env=dict(os.environ, KUMIKO_CEREBRO=str(cerebro)))
    try:
        if not s.abre():
            return False, nombre, 'sin respuesta al initialize'
        tools = [t['name'] for t in s.llama('tools/list').get('tools', [])]
        faltan = {'reglas_para_tarea', 'regla', 'defecto', 'checklist_entrega'} - set(tools)
        if faltan:
            return False, nombre, 'faltan herramientas: %s' % ', '.join(sorted(faltan))
        txt = s.herramienta('reglas_para_tarea', tarea=consulta_que_casa(cerebro))
        if not txt:
            return False, nombre, 'tools/call no devolvió contenido'
        if not re.search(r'`[A-Z]{2,3}(?:-[A-Z]{2,4})?-\d+`', txt):
            return False, nombre, 'la respuesta no trae ninguna regla: %s' % txt.split(chr(10))[0][:70]
        return True, nombre, '%d herramientas · %d caracteres con reglas dentro · mcp %s · %s' % (
            len(tools), len(txt), version_mcp, python if python != sys.executable else 'este python')
    except Exception as e:                                   # noqa: BLE001
        return False, nombre, '%s: %s' % (type(e).__name__, e)
    finally:
        s.cierra()


def prueba_sin_cerebro() -> tuple[bool, str, str]:
    """Quien acaba de instalar el plugin no tiene cerebro: el servidor debe arrancar
    igual y decir cómo crearlo, no morir y enseñar «failed» en /mcp."""
    nombre = 'el servidor arranca sin cerebro y explica qué hacer'
    encontrado = busca_python()
    if not encontrado:
        return False, nombre, PISTA_MCP
    python, _ = encontrado
    vacio = tempfile.mkdtemp(prefix='kumiko-sin-cerebro-')
    env = {k: v for k, v in os.environ.items() if k != 'KUMIKO_CEREBRO'}
    s = Sesion(python, cwd=vacio, env=env)
    try:
        if not s.abre():
            err = s.p.stderr.readline().strip() if s.p.poll() is not None else ''
            return False, nombre, 'el servidor muere al arrancar sin cerebro · %s' % (err or 'sin detalle')
        txt = s.herramienta('reglas_para_tarea', tarea='cualquier cosa')
        if 'inicia un cerebro kumiko' not in txt:
            return False, nombre, 'no explica cómo crear el cerebro: %s' % txt[:70]
        return True, nombre, 'responde con la forma de iniciarlo'
    except Exception as e:                                   # noqa: BLE001
        return False, nombre, '%s: %s' % (type(e).__name__, e)
    finally:
        s.cierra()
        shutil.rmtree(vacio, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
