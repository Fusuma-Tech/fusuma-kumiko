"""Telemetría del cerebro: qué se consulta, qué se devuelve, qué se encuentra.

Un fichero de líneas JSON en `.kumiko/consultas.jsonl` (ruta configurable en
`rutas.telemetria`). Lo escriben el servidor MCP y los hooks del harness; lo
lee el visor y `construir_indice.py`. No sale del repositorio del cerebro y
está en .gitignore por defecto: es material de trabajo, no fuente.

Para qué sirve: las consultas SIN resultado son los `aplica_si` que hay que
reescribir (o los sinónimos que faltan); los hallazgos por regla dicen qué
comprobaciones están parando errores de verdad; el cruce con las decisiones
«corregido» de las MR dice qué reglas no llegaron aunque se pidieran.
"""
from __future__ import annotations

import collections
import datetime
import json
import pathlib


def _ruta(cfg) -> pathlib.Path:
    return cfg.raiz / cfg.telemetria


def registra(cfg, origen: str, consulta: str = '', ids: list | None = None, **extra) -> None:
    """Una línea por evento. Nunca falla: la telemetría no puede tirar al servidor."""
    try:
        p = _ruta(cfg)
        p.parent.mkdir(parents=True, exist_ok=True)
        fila = dict(ts=datetime.datetime.now().isoformat(timespec='seconds'), origen=origen,
                    consulta=(consulta or '')[:300], ids=sorted(set(ids or [])))
        fila.update(extra)
        with p.open('a', encoding='utf-8') as f:
            f.write(json.dumps(fila, ensure_ascii=False) + '\n')
    except OSError:
        pass


def lee(cfg) -> list[dict]:
    p = _ruta(cfg)
    if not p.exists():
        return []
    filas = []
    for l in p.read_text(encoding='utf-8').split('\n'):
        l = l.strip()
        if not l:
            continue
        try:
            filas.append(json.loads(l))
        except json.JSONDecodeError:
            continue
    return filas


def resumen(cfg, maximo_listas: int = 12) -> dict:
    """Lo que el visor enseña y lo que `construir_indice.py` guarda en cerebro.json."""
    filas = lee(cfg)
    consultas = [f for f in filas if f.get('origen') in ('mcp', 'hook:prompt')]
    hallazgos = [f for f in filas if f.get('origen') in ('hook:editar', 'hook:parar', 'hook:commit')]
    con = [f for f in consultas if f.get('ids')]
    sin = [f for f in consultas if not f.get('ids')]
    reglas = collections.Counter(i for f in con for i in f['ids'])
    por_origen = collections.Counter(f.get('origen', '?') for f in filas)
    reglas_hall = collections.Counter(i for f in hallazgos for i in f.get('ids', []))
    bloqueos = sum(1 for f in hallazgos if f.get('bloqueo'))
    vistas_sin = set()
    ultimas_sin = []
    for f in reversed(sin):
        c = f.get('consulta', '').strip()
        if c and c.lower() not in vistas_sin:
            vistas_sin.add(c.lower()); ultimas_sin.append(dict(ts=f.get('ts', ''), consulta=c, origen=f.get('origen', '')))
        if len(ultimas_sin) >= maximo_listas:
            break
    return dict(
        eventos=len(filas),
        consultas=len(consultas),
        con_resultado=len(con),
        sin_resultado=len(sin),
        tasa_acierto=round(len(con) / len(consultas), 3) if consultas else None,
        por_origen=dict(por_origen),
        reglas_mas_devueltas=[dict(regla=r, veces=n) for r, n in reglas.most_common(maximo_listas)],
        hallazgos=len(hallazgos),
        bloqueos=bloqueos,
        reglas_con_hallazgos=[dict(regla=r, veces=n) for r, n in reglas_hall.most_common(maximo_listas)],
        ultimas_sin_resultado=ultimas_sin,
        desde=filas[0].get('ts', '') if filas else '',
        hasta=filas[-1].get('ts', '') if filas else '',
    )
