#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corre las comprobaciones del cerebro contra el código.

Es el tercer paso del ciclo. Una regla escrita no evita nada; una regla citable
evita algo; una regla **comprobada** es la única que impide repetir el error.
Cada fichero de reglas puede declarar en su frontmatter cómo se ve el
incumplimiento en el código, y este script lo busca:

    comprobaciones:
      - regla: DAT-PER-1
        patron: 'findOne\\('
        ficheros: 'src/main/**/*.kt'
        mensaje: leer y después escribir es una carrera
        bloquea: no

Uso:
    python3 motor/vigilar.py                  # el diff preparado (git add) del proyecto actual
    python3 motor/vigilar.py --todo           # todo el código del proyecto, no solo el diff
    python3 motor/vigilar.py --rama main      # lo que cambia respecto a una rama
    python3 motor/vigilar.py --listar         # qué comprobaciones tiene el cerebro
    python3 motor/vigilar.py --estricto       # cualquier aviso hace fallar (código 1)

Un resultado no es un defecto: es un sitio donde tienes que poder explicar por
qué está bien. Por eso por defecto solo avisa, y solo `bloquea: sí` corta.
"""
from __future__ import annotations

import argparse
import fnmatch
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from nucleo import Cerebro, Config, localiza  # noqa: E402

GRIS, ROJO, AMBAR, VERDE, NEGRITA, FIN = '\033[90m', '\033[31m', '\033[33m', '\033[32m', '\033[1m', '\033[0m'
IGNORAR = ('.git/', 'node_modules/', 'dist/', 'build/', '.kumiko/', '__pycache__/', 'target/')


def lineas_del_diff(proyecto: pathlib.Path, rama: str | None) -> dict[str, list[tuple[int, str]]]:
    """{ruta: [(nº línea, texto)]} solo con las líneas AÑADIDAS."""
    base = ['git', '-C', str(proyecto), 'diff', '-U0', '--no-color']
    cmd = base + ([rama + '...HEAD'] if rama else ['--cached'])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit('git diff ha fallado: %s' % r.stderr.strip())
    salida: dict[str, list] = {}
    ruta, n = None, 0
    for l in r.stdout.split('\n'):
        if l.startswith('+++ b/'):
            ruta = l[6:]; salida.setdefault(ruta, [])
        elif l.startswith('@@'):
            m = re.search(r'\+(\d+)', l); n = int(m.group(1)) if m else 0
        elif ruta and l.startswith('+') and not l.startswith('+++'):
            salida[ruta].append((n, l[1:])); n += 1
        elif ruta and not l.startswith('-'):
            n += 1
    return salida


def lineas_del_arbol(proyecto: pathlib.Path) -> dict[str, list[tuple[int, str]]]:
    salida = {}
    for p in proyecto.rglob('*'):
        if not p.is_file():
            continue
        rel = str(p.relative_to(proyecto))
        if any(x in rel for x in IGNORAR) or p.suffix in ('.png', '.jpg', '.pdf', '.lock', '.jar'):
            continue
        try:
            texto = p.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        salida[rel] = list(enumerate(texto.split('\n'), 1))
    return salida


def lineas_de_ficheros(proyecto: pathlib.Path, rutas: list[str]) -> dict[str, list[tuple[int, str]]]:
    """Ficheros concretos (el que el agente acaba de editar), enteros."""
    salida = {}
    for r in rutas:
        p = pathlib.Path(r)
        if not p.is_absolute():
            p = proyecto / p
        if not p.is_file():
            continue
        try:
            rel = str(p.resolve().relative_to(proyecto.resolve()))
        except ValueError:
            rel = str(p)
        try:
            salida[rel] = list(enumerate(p.read_text(encoding='utf-8').split('\n'), 1))
        except (UnicodeDecodeError, OSError):
            continue
    return salida


def lineas_de_cambios(proyecto: pathlib.Path) -> dict[str, list[tuple[int, str]]]:
    """Todo lo que aún no está en HEAD: líneas añadidas en el diff (preparado o no)
    y los ficheros nuevos sin seguimiento. Es lo que el hook de parada revisa."""
    salida: dict[str, list] = {}
    r = subprocess.run(['git', '-C', str(proyecto), 'diff', 'HEAD', '-U0', '--no-color'], capture_output=True, text=True)
    if r.returncode != 0:  # sin commits todavía, o sin git: el árbol entero
        return lineas_del_arbol(proyecto)
    ruta, n = None, 0
    for l in r.stdout.split('\n'):
        if l.startswith('+++ b/'):
            ruta = l[6:]; salida.setdefault(ruta, [])
        elif l.startswith('@@'):
            m = re.search(r'\+(\d+)', l); n = int(m.group(1)) if m else 0
        elif ruta and l.startswith('+') and not l.startswith('+++'):
            salida[ruta].append((n, l[1:])); n += 1
        elif ruta and not l.startswith('-'):
            n += 1
    r = subprocess.run(['git', '-C', str(proyecto), 'ls-files', '--others', '--exclude-standard'], capture_output=True, text=True)
    nuevos = [x for x in r.stdout.split('\n') if x.strip()]
    salida.update(lineas_de_ficheros(proyecto, nuevos))
    return salida


def busca_hallazgos(c: Cerebro, fuentes: dict[str, list[tuple[int, str]]]) -> list[dict]:
    """Aplica las comprobaciones del cerebro a {ruta: [(línea, texto)]}.
    Es lo que comparten la línea de comandos, el pre-commit y los hooks."""
    compiladas = [(re.compile(x['patron']), x) for x in c.comprobaciones()]
    hallazgos = []
    for rel, lineas in fuentes.items():
        for rx, x in compiladas:
            if not casa_ficheros(rel, x['ficheros']):
                continue
            for n, texto in lineas:
                if rx.search(texto):
                    hallazgos.append(dict(regla=x['regla'], ruta=rel, linea=n, texto=texto.strip(),
                                          mensaje=x['mensaje'], bloquea=x['bloquea'], fuente=x['ruta']))
    return hallazgos


def casa_ficheros(rel: str, patron: str) -> bool:
    """`src/**/*.kt` casa como espera la gente: `**` cruza directorios."""
    patrones = [x.strip() for x in patron.split(',') if x.strip()]
    for pat in patrones:
        if fnmatch.fnmatch(rel, pat):
            return True
        if '**' in pat and fnmatch.fnmatch(rel, pat.replace('**/', '')):
            return True
        if '**' in pat and re.fullmatch(
                re.escape(pat).replace(r'\*\*/', '(?:.*/)?').replace(r'\*\*', '.*').replace(r'\*', '[^/]*'), rel):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--proyecto', default='.', help='raíz del código (por defecto, el directorio actual)')
    ap.add_argument('--cerebro', help='raíz del cerebro (si no, se localiza como el servidor)')
    ap.add_argument('--todo', action='store_true', help='todo el código, no solo el diff')
    ap.add_argument('--rama', help='comparar con una rama: lo que cambia respecto a ella')
    ap.add_argument('--listar', action='store_true', help='enseñar las comprobaciones del cerebro y salir')
    ap.add_argument('--estricto', action='store_true', help='cualquier aviso corta (código 1)')
    a = ap.parse_args()

    proyecto = pathlib.Path(a.proyecto).resolve()
    c = Cerebro(Config(localiza(a.cerebro or str(proyecto))))
    comps = c.comprobaciones()

    if a.listar:
        print('\n%s · %d comprobaciones ejecutables sobre %d reglas\n' % (c.cfg.nombre, len(comps), len(c.reglas)))
        for x in comps:
            print('  %-12s %-34s %s%s%s' % (x['regla'], x['patron'][:34], GRIS, x['ficheros'], FIN))
            print('  %-12s %s%s%s' % ('', GRIS, x['mensaje'][:90], FIN))
        cubiertas = {x['regla'] for x in comps}
        print('\n  %d de %d reglas tienen comprobación automática. El resto son de juicio, y está bien.'
              % (len(cubiertas & set(c.reglas)), len(c.reglas)))
        return 0

    if not comps:
        print('Este cerebro no declara comprobaciones. Añade `comprobaciones:` al frontmatter de una regla.')
        return 0

    try:
        fuentes = lineas_del_arbol(proyecto) if a.todo else lineas_del_diff(proyecto, a.rama)
        origen = 'todo el árbol' if a.todo else ('cambios respecto a %s' % a.rama if a.rama else 'el diff preparado')
    except SystemExit as e:
        if a.todo:
            raise
        print('%s%s%s\nSin git aquí: usa --todo para revisar el árbol entero.' % (ROJO, e, FIN))
        return 2

    hallazgos = [(dict(regla=h['regla'], bloquea=h['bloquea'], mensaje=h['mensaje'], ruta=h['fuente']),
                  h['ruta'], h['linea'], h['texto']) for h in busca_hallazgos(c, fuentes)]

    print('\n%svigilar%s · %s · %s · %d comprobaciones\n' % (NEGRITA, FIN, c.cfg.nombre, origen, len(comps)))
    if not hallazgos:
        print('  %s✓ nada que explicar%s\n' % (VERDE, FIN))
        return 0

    bloquean = 0
    for x, rel, n, texto in hallazgos:
        color = ROJO if x['bloquea'] else AMBAR
        bloquean += x['bloquea']
        print('  %s%-12s%s %s:%d' % (color + NEGRITA, x['regla'], FIN, rel, n))
        print('  %s%s%s' % (GRIS, '             ' + texto[:100], FIN))
        print('             ↳ %s  %s%s%s' % (x['mensaje'], GRIS, x['ruta'], FIN))
        print()

    print('  %d sitios. Un resultado no es un defecto: es un sitio donde tienes que poder explicar'
          ' por qué está bien.' % len(hallazgos))
    print('  Texto completo de cada regla: `regla("<id>")` en el MCP, o grep del id en el cerebro.\n')
    if bloquean or a.estricto:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
