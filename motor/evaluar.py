"""Evalúa el enrutado del cerebro contra consultas con respuesta conocida.

    python3 motor/evaluar.py                 # sobre el cerebro que localice
    python3 motor/evaluar.py /mi/cerebro
    python3 motor/evaluar.py --json          # solo el resultado, para el visor/CI

El conjunto vive en `evaluaciones/consultas.jsonl` (ruta en `rutas.evaluaciones`),
una consulta por línea:

    {"consulta": "guardo una reserva y quiero evitar solapes",
     "esperadas": ["DAT-PER-1", "DAT-PER-2"],
     "no_esperadas": ["TST-3"]}

`esperadas` son los ids que DEBEN salir; `no_esperadas`, los que no deben salir
(opcional). Una consulta con `esperadas: []` comprueba que el cerebro sabe
callarse. Se miden recall (de lo esperado, cuánto salió) y precisión (de lo que
salió, cuánto era esperado), por consulta y en total. Sale con código 1 si el
recall medio queda por debajo de `evaluacion.umbral_recall` (0,8 por defecto).

De dónde salen las consultas: de la telemetría. Las que el harness registró sin
resultado y luego alguien resolvió a mano son exactamente las que hay que meter
aquí, con el id que tendría que haber salido. Así cada fallo de enrutado se
convierte en un caso de prueba y el `aplica_si` deja de retocarse a ciegas.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from nucleo import Cerebro, Config, localiza  # noqa: E402

GRIS, ROJO, VERDE, NEGRITA, FIN = '\033[90m', '\033[31m', '\033[32m', '\033[1m', '\033[0m'


def carga_casos(cfg) -> list[dict]:
    p = cfg.raiz / cfg.evaluaciones
    if not p.exists():
        return []
    casos = []
    for n, l in enumerate(p.read_text(encoding='utf-8').split('\n'), 1):
        l = l.strip()
        if not l or l.startswith('#'):
            continue
        try:
            d = json.loads(l)
        except json.JSONDecodeError as e:
            raise SystemExit('%s:%d no es JSON: %s' % (p, n, e))
        casos.append(dict(consulta=d['consulta'], esperadas=list(d.get('esperadas', [])),
                          no_esperadas=list(d.get('no_esperadas', []))))
    return casos


def evalua(c: Cerebro) -> dict:
    casos = carga_casos(c.cfg)
    filas = []
    for k in casos:
        aciertos = c.busca(k['consulta'])
        salieron = [rid for _, _, reglas in aciertos for rid, _ in reglas]
        esp, no_esp = set(k['esperadas']), set(k['no_esperadas'])
        s = set(salieron)
        recall = (len(esp & s) / len(esp)) if esp else (1.0 if not (s & no_esp) else 0.0)
        precision = (len(esp & s) / len(s)) if s and esp else (1.0 if not s or not esp else 0.0)
        indebidas = sorted(s & no_esp)
        filas.append(dict(consulta=k['consulta'], esperadas=sorted(esp), salieron=salieron,
                          faltan=sorted(esp - s), indebidas=indebidas,
                          recall=round(recall, 3), precision=round(precision, 3),
                          ok=not (esp - s) and not indebidas))
    n = len(filas)
    recall = round(sum(f['recall'] for f in filas) / n, 3) if n else None
    precision = round(sum(f['precision'] for f in filas) / n, 3) if n else None
    return dict(casos=n, ok=sum(1 for f in filas if f['ok']), recall=recall, precision=precision,
                umbral_recall=c.cfg.umbral_recall, pasa=(recall is None or recall >= c.cfg.umbral_recall),
                fichero=c.cfg.evaluaciones, filas=filas)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    c = Cerebro(Config(localiza(args[0] if args else None)))
    r = evalua(c)
    if '--json' in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r['pasa'] else 1
    print('\n%sevaluar%s · %s · %d consultas en %s\n' % (NEGRITA, FIN, c.cfg.nombre, r['casos'], r['fichero']))
    if not r['casos']:
        print('  Sin conjunto de evaluación. Crea %s con una consulta por línea:' % r['fichero'])
        print('  {"consulta": "…", "esperadas": ["ID-1"]}\n')
        return 0
    for f in r['filas']:
        marca = (VERDE + '✓') if f['ok'] else (ROJO + '✗')
        print('  %s%s %s' % (marca, FIN, f['consulta'][:80]))
        if f['faltan']:
            print('     %sfaltan: %s%s' % (ROJO, ', '.join(f['faltan']), FIN))
        if f['indebidas']:
            print('     %sindebidas: %s%s' % (ROJO, ', '.join(f['indebidas']), FIN))
        print('     %ssalieron: %s%s' % (GRIS, ', '.join(f['salieron']) or '—', FIN))
    color = VERDE if r['pasa'] else ROJO
    print('\n  %srecall %.0f%% · precisión %.0f%% · %d de %d consultas bien · umbral %.0f%%%s\n'
          % (color, r['recall'] * 100, r['precision'] * 100, r['ok'], r['casos'], r['umbral_recall'] * 100, FIN))
    return 0 if r['pasa'] else 1


if __name__ == '__main__':
    sys.exit(main())
