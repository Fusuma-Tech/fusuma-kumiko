#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Servidor MCP de kumiko: sirve el cerebro por tarea, no por fichero.

En vez de cargar el cerebro entero en el contexto, el agente dice lo que va a
hacer y recibe **solo** las reglas aplicables con sus ids. Si necesita el texto
completo de una, la pide.

    python3 motor/servidor_mcp.py [ruta-al-cerebro]     # servidor por stdio
    python3 motor/servidor_mcp.py --probar "..."        # ver qué devolvería
    python3 motor/servidor_mcp.py --medir               # coste frente a cargarlo todo

La raíz del cerebro se busca subiendo directorios desde donde se ejecuta, o se
pasa por argumento, o por la variable de entorno KUMIKO_CEREBRO.
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from nucleo import Cerebro, Config, localiza  # noqa: E402

TAREAS_DEMO = [
    'guardo un registro nuevo y tengo que evitar duplicados',
    'añado un endpoint que dispara un proceso en segundo plano',
    'comparo importes para decidir si hay saldo suficiente',
    'escribo los tests de un adaptador',
    'documento una función con un comentario',
]


def carga(argumento=None) -> Cerebro:
    return Cerebro(Config(localiza(argumento)))


def servidor(ruta: str | None = None) -> None:
    from mcp.server.mcpserver import MCPServer

    c = carga(ruta)
    cfg = c.cfg
    app = MCPServer(
        name='kumiko',
        version='0.1.0',
        instructions=(
            'Cerebro de contexto del proyecto «%s». Llama a `reglas_para_tarea` ANTES de '
            'escribir código, con una frase de lo que vas a tocar: devuelve solo las reglas '
            'aplicables, no el cerebro entero. Cita los ids en la MR. Antes de decir que algo '
            'está hecho, llama a `checklist_entrega`. Cuando una revisión te pille algo que no '
            'estaba escrito, dilo: es material para una regla nueva.' % cfg.nombre),
    )

    @app.tool(description=(
        'Devuelve las reglas del cerebro que aplican a lo que vas a hacer. Descríbelo con los '
        'términos técnicos que vas a tocar. Opcionalmente filtra por momento del trabajo.'))
    def reglas_para_tarea(tarea: str, momento: str | None = None) -> str:
        return c.responde(tarea, momento)

    @app.tool(description='Texto completo de una regla por su id.')
    def regla(id: str) -> str:
        return c.texto(id.strip()) or 'No existe la regla «%s». Mira `%s`.' % (id, cfg.salida_indice)

    @app.tool(description='Texto completo de un defecto ya pagado, por su id: §32, §7…')
    def defecto(id: str) -> str:
        i = id.strip()
        i = i if i.startswith('§') else '§' + i.lstrip('#§')
        return c.texto(i) or 'No existe el defecto «%s».' % id

    @app.tool(description=(
        'La lista de comprobación previa a la entrega. Llámalo al terminar cualquier cambio, '
        'antes de decir que está hecho.'))
    def checklist_entrega() -> str:
        from nucleo import lee_frontmatter
        for f in c.ficheros.values():
            if f['tipo'] == 'checklist':
                bruto = c.cfg.raiz.joinpath(f['ruta']).read_text(encoding='utf-8')
                return lee_frontmatter(bruto)[1].strip()   # el frontmatter no le sirve al agente
        return 'Este cerebro todavía no tiene una lista de entrega (`tipo: checklist`).'

    @app.tool(description=(
        'Busca un término literal en todo el cerebro y devuelve los ids donde aparece. Para '
        'cuando sabes la palabra exacta.'))
    def buscar(texto: str, maximo: int = 15) -> str:
        pat = re.compile(re.escape(texto), re.I)
        salida = []
        for p in cfg.markdown():
            actual = None
            for linea in p.read_text(encoding='utf-8').split('\n'):
                m = re.match(r'^#{2,3} ([A-Z][\w-]*-\d+|§\d+) · ', linea)
                if m:
                    actual = m.group(1)
                if pat.search(linea):
                    salida.append('%-12s %-30s %s' % (
                        actual or '—', str(p.relative_to(cfg.raiz))[:30], linea.strip()[:90]))
                if len(salida) >= maximo:
                    return '\n'.join(salida)
        return '\n'.join(salida) if salida else 'Sin resultados para «%s».' % texto

    @app.tool(description=(
        'Mapa del cerebro: categorías, momentos y ficheros. Para orientarse la primera vez o '
        'cuando `reglas_para_tarea` no encuentra nada.'))
    def mapa() -> str:
        L = ['# %s' % cfg.nombre, '']
        for cat in cfg.categorias:
            fs = [f for f in c.ficheros.values() if f['categoria'] == cat['id']]
            if not fs:
                continue
            L.append('## %s — %s' % (cat['nombre'], cat.get('descripcion', '')))
            for f in fs:
                L.append('- `%s` %s · %d reglas · %s'
                         % (f['id'], f['titulo'], len(c.por_fichero.get(f['id'], [])), f['ruta']))
            L.append('')
        L.append('Momentos: %s' % ', '.join(m['id'] for m in cfg.momentos))
        L.append('Defectos registrados: %d' % len(c.defectos))
        return '\n'.join(L)

    app.run()


def probar(tarea: str, ruta=None) -> None:
    salida = carga(ruta).responde(tarea)
    print(salida)
    print('\n--- %s caracteres devueltos ---' % format(len(salida), ','))


def medir(ruta=None) -> None:
    c = carga(ruta)
    todo = sum(len(p.read_text(encoding='utf-8')) for p in c.cfg.markdown())
    print('%s\n' % c.cfg.nombre)
    print('Cerebro completo en contexto: %s caracteres (~%s tokens)\n'
          % (format(todo, ','), format(round(todo / 3.6), ',')))
    print('%-56s %9s %9s' % ('tarea', 'chars', 'factor'))
    print('-' * 78)
    total = 0
    for t in TAREAS_DEMO:
        n = len(c.responde(t))
        total += n
        print('%-56s %9s %8.0fx' % (t[:56], format(n, ','), todo / n))
    media = total / len(TAREAS_DEMO)
    print('-' * 78)
    print('%-56s %9s %8.0fx' % ('media', format(round(media), ','), todo / media))
    print('\nTokens aproximados (÷3.6). Los factores no dependen del tokenizador.')


if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == '--medir':
        medir(args[1] if len(args) > 1 else None)
    elif args and args[0] == '--probar':
        probar(' '.join(args[1:]) or 'guardo un registro nuevo')
    else:
        servidor(args[0] if args else None)
