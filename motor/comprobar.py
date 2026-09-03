#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba la integridad del cerebro. Falla con código 1 si algo no cuadra.

Vale tal cual en un hook de pre-commit o en CI.

    python3 motor/comprobar.py [ruta-al-cerebro]

Cinco comprobaciones:
  1. Toda ruta `.md` citada dentro del cerebro existe.
  2. Todo id citado (`ARQ-ERR-2`, `§32`) tiene su encabezado.
  3. Todo fichero de reglas lleva frontmatter completo y válido.
  4. Ningún id está duplicado.
  5. El índice de defectos cuadra con sus secciones.
"""
from __future__ import annotations

import pathlib
import posixpath
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from nucleo import (CAMPOS_FRONTMATTER, Cerebro, Config, localiza,  # noqa: E402
                    lee_frontmatter)

RE_CITA_RUTA = re.compile(r'`((?:\.\./)*[\w./-]+\.md)`')
RE_CITA_ID = re.compile(r'`((?!DEV-|TODO-)[A-Z]{2,3}(?:-[A-Z]{2,4})?-\d+)`')
RE_CITA_DEF = re.compile(r'§(\d+)')


def main() -> int:
    raiz = localiza(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    cfg = Config(raiz)
    c = Cerebro(cfg)
    fallos: list[str] = []

    ids = set(c.reglas) | set(c.defectos) | set(c.ficheros)
    externos = tuple(cfg.bruto.get('rutas_externas', []))

    for p in cfg.markdown():
        rel = str(p.relative_to(raiz))
        aqui = posixpath.dirname(rel)
        t = p.read_text(encoding='utf-8')
        # una carpeta puede hablar *sobre* el cerebro sin ser parte de su grafo
        if not any(rel.startswith(x) for x in cfg.bruto.get('solo_prosa', [])):
            for m in RE_CITA_RUTA.finditer(t):
                if externos and m.group(1).startswith(externos):
                    continue
                if not (raiz / posixpath.normpath(posixpath.join(aqui or '.', m.group(1)))).exists():
                    fallos.append('ruta rota · %s → %s' % (rel, m.group(1)))
        for m in RE_CITA_ID.finditer(t):
            if m.group(1) not in ids:
                fallos.append('id inexistente · %s → %s' % (rel, m.group(1)))
        for m in RE_CITA_DEF.finditer(t):
            if '§' + m.group(1) not in c.defectos:
                fallos.append('defecto inexistente · %s → §%s' % (rel, m.group(1)))

    for p in cfg.markdown():
        rel = str(p.relative_to(raiz))
        if rel == cfg.router or rel == cfg.defectos:
            continue
        if not any(rel.startswith(cfg.dir_reglas) or rel.startswith(e) for e in cfg.extra):
            continue
        fm, _ = lee_frontmatter(p.read_text(encoding='utf-8'))
        if not fm:
            fallos.append('sin frontmatter · %s' % rel)
            continue
        for campo in CAMPOS_FRONTMATTER:
            if campo not in fm:
                fallos.append('frontmatter incompleto · %s → falta "%s"' % (rel, campo))
        if fm.get('categoria') and fm['categoria'] not in cfg.ids_categoria:
            fallos.append('categoría desconocida · %s → %s' % (rel, fm['categoria']))
        for mo in fm.get('momentos', []):
            if mo not in cfg.ids_momento:
                fallos.append('momento desconocido · %s → %s' % (rel, mo))

    vistos: dict[str, str] = {}
    for rid, r in c.reglas.items():
        if rid in vistos and vistos[rid] != r['ruta']:
            fallos.append('id duplicado · %s en %s y %s' % (rid, vistos[rid], r['ruta']))
        vistos[rid] = r['ruta']

    pd = raiz / cfg.defectos
    if pd.exists():
        t = pd.read_text(encoding='utf-8')
        sec = [m.group(1) for m in re.finditer(r'^## (§\d+) · ', t, re.M)]
        fil = [m.group(1) for m in re.finditer(r'^\| `?(§\d+)`? \|', t, re.M)]
        if fil:
            for x in set(fil) - set(sec):
                fallos.append('el índice tiene una fila sin sección · %s' % x)
            for x in set(sec) - set(fil):
                fallos.append('sección sin fila en el índice · %s' % x)
        for x in {s for s in sec if sec.count(s) > 1}:
            fallos.append('sección de defecto duplicada · %s' % x)

    # aviso, no fallo: una regla reincidente sin comprobación automática es la
    # candidata número uno a tenerla. Se dice, y se sigue.
    cubiertas = {x['regla'] for x in c.comprobaciones()}
    avisos = [x for x in c.reincidencias() if x['regla'] not in cubiertas]
    if avisos:
        print('%d reglas reincidentes sin comprobación automática:' % len(avisos))
        for x in avisos:
            print('  %-12s %d veces · %s' % (x['regla'], x['veces'], x['titulo'][:60]))
        print('  → son las primeras candidatas a un `comprobaciones:` en su frontmatter\n')

    if fallos:
        print('%d problemas:\n' % len(fallos))
        for f in sorted(set(fallos)):
            print('  ' + f)
        return 1
    print('cerebro coherente · %d ids · %d ficheros revisados' % (len(ids), len(cfg.markdown())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
