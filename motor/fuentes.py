#!/usr/bin/env python3
"""Detecta cuándo un nodo del cerebro describe código que ya ha cambiado.

`comprobar.py` valida ids, rutas y frontmatter: que el cerebro sea *coherente*.
No valida que lo escrito siga siendo *verdad*. Y un nodo `tipo: contexto` —el
que explica un proceso— envejece de otra forma que una regla: el día que alguien
reordena las tareas de un workflow, la prosa que las enumera pasa a mentir y
nada lo dice.

`fuentes:` ancla un fichero del cerebro a los ficheros de código que describe,
guardando el hash que tenían **cuando una persona lo verificó**:

    fuentes:
      - ruta: apps/workflows-api/src/workflows/conta/new-expense/new-expense.workflow.ts
        hash: a3f9c1d2e4b5

El hash se guarda en el markdown, no en el índice generado, a propósito: si
viviera en el índice, regenerarlo lo actualizaría solo y el desfase no se
detectaría nunca. Aquí solo cambia cuando alguien decide que ha vuelto a mirar.

    python3 motor/fuentes.py --revisar          # qué nodos describen código que cambió
    python3 motor/fuentes.py --fijar PRO-FAC    # vuelve a anclar, DESPUÉS de releerlo
    python3 motor/fuentes.py --fijar todos

`--fijar` es lo que se hace después de comprobar que el nodo sigue siendo
cierto, nunca antes: fijar sin releer convierte esto en un sello de goma.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from nucleo import Cerebro, Config, localiza  # noqa: E402

LARGO_HASH = 12


def hash_de(p: pathlib.Path) -> str | None:
    """sha256 truncado del contenido. None si el fichero ya no existe."""
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:LARGO_HASH]
    except OSError:
        return None


def _fuentes_de(f: dict) -> list[dict]:
    return [x for x in f.get('fuentes', []) if isinstance(x, dict) and x.get('ruta')]


def desfases(c: Cerebro, proyecto: pathlib.Path,
             solo_rutas: set[str] | None = None) -> list[dict]:
    """Fuentes cuyo hash actual no coincide con el anclado.

    `solo_rutas` acota a los ficheros que acaban de tocarse (lo que usa el hook);
    sin él, revisa el cerebro entero.
    """
    salida = []
    for f in c.ficheros.values():
        for src in _fuentes_de(f):
            ruta = str(src['ruta']).strip()
            if solo_rutas is not None and ruta not in solo_rutas:
                continue
            actual = hash_de(proyecto / ruta)
            anclado = str(src.get('hash', '')).strip()
            if actual == anclado:
                continue
            salida.append(dict(
                nodo=f['id'], titulo=f.get('titulo', f['id']), nodo_ruta=f['ruta'],
                ruta=ruta, anclado=anclado, actual=actual,
                motivo='desaparecido' if actual is None else 'cambiado'))
    return salida


def rutas_vigiladas(c: Cerebro) -> set[str]:
    """Todas las rutas de código que algún nodo dice describir."""
    return {str(s['ruta']).strip() for f in c.ficheros.values() for s in _fuentes_de(f)}


def fija(c: Cerebro, proyecto: pathlib.Path, ids: list[str]) -> list[str]:
    """Reescribe los hashes anclados de los nodos indicados. Devuelve lo tocado."""
    tocados = []
    for f in c.ficheros.values():
        if ids != ['todos'] and f['id'] not in ids:
            continue
        fuentes = _fuentes_de(f)
        if not fuentes:
            continue
        p = c.cfg.raiz / f['ruta']
        texto = p.read_text(encoding='utf-8')
        cambiado = False
        for src in fuentes:
            ruta = str(src['ruta']).strip()
            actual = hash_de(proyecto / ruta)
            if actual is None:
                print('  ! %s: %s no existe; no lo fijo' % (f['id'], ruta))
                continue
            if actual == str(src.get('hash', '')).strip():
                continue
            # Sustituye solo el hash del bloque de ESTA ruta, sin tocar el resto
            patron = re.compile(
                r'(-\s+ruta:\s*%s\s*\n\s+hash:\s*)([0-9a-f]*)' % re.escape(ruta))
            texto, n = patron.subn(lambda m: m.group(1) + actual, texto, count=1)
            if n:
                cambiado = True
        if cambiado:
            p.write_text(texto, encoding='utf-8')
            tocados.append(f['id'])
    return tocados


def formatea(ds: list[dict], maximo: int = 8) -> str:
    L = []
    for d in ds[:maximo]:
        que = ('el fichero ya no existe' if d['motivo'] == 'desaparecido'
               else 'ha cambiado desde la última vez que se verificó')
        L.append('- `%s` %s\n  describe `%s`, que %s.\n  Relee el nodo (%s); si sigue siendo '
                 'cierto: `python3 motor/fuentes.py --fijar %s`'
                 % (d['nodo'], d['titulo'], d['ruta'], que, d['nodo_ruta'], d['nodo']))
    if len(ds) > maximo:
        L.append('- … y %d más' % (len(ds) - maximo))
    return '\n'.join(L)


def main() -> int:
    args = [a for a in sys.argv[1:]]
    proyecto = pathlib.Path.cwd()
    c = Cerebro(Config(localiza(str(proyecto))))

    if '--fijar' in args:
        ids = args[args.index('--fijar') + 1:]
        if not ids:
            print('¿fijar qué? un id de fichero (PRO-FAC) o `todos`.')
            return 2
        tocados = fija(c, proyecto, ids)
        print('fijados: %s' % (', '.join(tocados) if tocados else 'nada que fijar'))
        return 0

    vigiladas = rutas_vigiladas(c)
    ds = desfases(c, proyecto)
    if not ds:
        print('%d fuente(s) ancladas · ninguna ha cambiado' % len(vigiladas))
        return 0
    print('%d nodo(s) describen código que ha cambiado:\n' % len(ds))
    print(formatea(ds, maximo=50))
    print('\nUn desfase no es un error: es un nodo que hay que releer antes de fiarse.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
