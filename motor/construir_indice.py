#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera el índice y los datos del cerebro a partir del markdown.

El markdown es la única fuente de verdad. Este script no inventa nada: lee el
frontmatter y los encabezados con id. Si escribes el índice a mano, miente en
dos semanas.

    python3 motor/construir_indice.py [ruta-al-cerebro]
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from nucleo import Cerebro, Config, busca_raiz  # noqa: E402


def datos(c: Cerebro) -> dict:
    cfg = c.cfg
    return dict(
        nombre=cfg.nombre,
        generado=datetime.date.today().isoformat(),
        categorias=cfg.categorias,
        momentos=cfg.momentos,
        ficheros=[{k: v for k, v in f.items()} for f in c.ficheros.values()],
        reglas=[{k: v for k, v in r.items() if k != 'cuerpo'} for r in c.reglas.values()],
        defectos=[{k: v for k, v in d.items() if k != 'cuerpo'} for d in c.defectos.values()],
        comprobaciones=c.comprobaciones(),
        reincidencias=c.reincidencias(),
    )


def indice(c: Cerebro) -> str:
    cfg = c.cfg
    L = ['# Índice del cerebro · %s\n' % cfg.nombre]
    L.append('> Generado por `motor/construir_indice.py`. **No lo edites a mano**: cambia la')
    L.append('> regla en su fichero y vuelve a ejecutarlo.\n')
    L.append('Cada regla tiene un id citable. `grep -rn "<id>" .` lleva al texto exacto.\n')

    L.append('## Por momento\n')
    L.append('| Momento | Qué leer |')
    L.append('|---|---|')
    for m in cfg.momentos:
        fs = [f for f in c.ficheros.values() if m['id'] in f['momentos']]
        celda = ', '.join('[`%s`](%s)' % (f['id'], rel(cfg, f['ruta'])) for f in fs) or '—'
        L.append('| **%s** | %s |' % (m['nombre'], celda))
    L.append('')

    for cat in cfg.categorias:
        fs = [f for f in c.ficheros.values() if f['categoria'] == cat['id']]
        if not fs:
            continue
        L.append('## %s\n' % cat['nombre'])
        L.append('%s\n' % cat.get('descripcion', ''))
        for f in fs:
            L.append('### [`%s` · %s](%s)\n' % (f['id'], f['titulo'], rel(cfg, f['ruta'])))
            if f['aplica_si']:
                L.append('**Aplica si:** %s\n' % f['aplica_si'])
            if f['senal']:
                L.append('**Se detecta por:** %s\n' % f['senal'])
            reglas = [c.reglas[r] for r in c.por_fichero.get(f['id'], [])]
            if reglas:
                L.append('| Id | Regla | Qué dice |')
                L.append('|---|---|---|')
                for r in reglas:
                    L.append('| `%s` | %s | %s |' % (r['id'], r['titulo'], r['resumen']))
            elif f['resumen']:
                L.append(f['resumen'])
            L.append('')

    comps = c.comprobaciones()
    cubiertas = {x['regla'] for x in comps} & set(c.reglas)
    rein = c.reincidencias()
    L.append('## Salud del cerebro\n')
    L.append('| | |')
    L.append('|---|---|')
    L.append('| Reglas con comprobación automática | %d de %d |' % (len(cubiertas), len(c.reglas)))
    L.append('| Reglas reincidentes | %d |' % len(rein))
    L.append('')
    if rein:
        L.append('**Reincidentes** — reglas que ya estaban escritas y volvieron a fallar. No les falta')
        L.append('existir: les falta llegar a tiempo. Son las primeras candidatas a una comprobación automática.\n')
        L.append('| Regla | Veces | Corregida en | Defectos |')
        L.append('|---|---|---|---|')
        for x in rein:
            L.append('| `%s` %s | %d | %s | %s |' % (
                x['regla'], x['titulo'], x['veces'],
                ', '.join(x['corregido_en']) or '—',
                ', '.join('`%s`' % d for d in x['defectos']) or '—'))
        L.append('')

    if c.defectos:
        L.append('## Defectos ya pagados\n')
        L.append('Los %d casos reales de [`%s`](%s), con la regla que los habría evitado.\n'
                 % (len(c.defectos), cfg.defectos, rel(cfg, cfg.defectos)))
        L.append('| Id | Defecto | Regla |')
        L.append('|---|---|---|')
        for d in c.defectos.values():
            L.append('| `%s` | %s | %s |'
                     % (d['id'], d['titulo'], ('`%s`' % d['regla']) if d['regla'] else '—'))
        L.append('')
    return '\n'.join(L)


def rel(cfg: Config, ruta: str) -> str:
    import posixpath
    base = posixpath.dirname(cfg.salida_indice)
    return posixpath.relpath(ruta, base or '.')


def main() -> None:
    raiz = busca_raiz(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    cfg = Config(raiz)
    c = Cerebro(cfg)

    pi = raiz / cfg.salida_indice
    pi.parent.mkdir(parents=True, exist_ok=True)
    pi.write_text(indice(c), encoding='utf-8')

    pd = raiz / cfg.salida_datos
    pd.parent.mkdir(parents=True, exist_ok=True)
    pd.write_text(json.dumps(datos(c), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print('%s · %d reglas en %d ficheros · %d defectos'
          % (cfg.nombre, len(c.reglas), len(c.ficheros), len(c.defectos)))
    print('escritos: %s, %s' % (cfg.salida_indice, cfg.salida_datos))


if __name__ == '__main__':
    main()
