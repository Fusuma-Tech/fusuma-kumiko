# -*- coding: utf-8 -*-
"""Núcleo de kumiko: configuración, carga del cerebro y emparejado.

Un *cerebro* es una carpeta con markdown y un `kumiko.json` en la raíz. Nada
está cableado: las rutas, las categorías y los momentos salen de ese fichero.

Vocabulario, porque el resto del código lo usa sin explicarlo:

- **fichero**  un markdown con frontmatter. Agrupa reglas de un mismo tema.
- **regla**    un encabezado con id dentro de un fichero: `## ARQ-ERR-2 · …`.
- **defecto**  un caso real que ya costó caro: `## §32 · …`.
- **núcleo**   las reglas de método, que viven en el router y aplican siempre.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import unicodedata

NOMBRE_CONFIG = 'kumiko.json'

RE_FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)
RE_REGLA = re.compile(r'^#{2,3} ([A-Z]{2,3}(?:-[A-Z]{2,4})?-\d+) · (.+)$', re.M)
RE_DEFECTO = re.compile(r'^## (§\d+) · (.+)$', re.M)
RE_CHECK = re.compile(r'^\d+\. `([A-Z]{2,4}-\d+)` \*\*(.+?)\*\*(.*)$', re.M)

CAMPOS_FRONTMATTER = ['id', 'tipo', 'categoria', 'momentos', 'resumen']

VACIAS = {
    'para', 'por', 'que', 'con', 'los', 'las', 'del', 'una', 'uno', 'unos', 'unas', 'este',
    'esta', 'esto', 'estos', 'estas', 'como', 'cuando', 'donde', 'desde', 'hasta', 'sobre',
    'entre', 'todo', 'toda', 'todos', 'todas', 'algo', 'algun', 'alguna', 'otro', 'otra',
    'mismo', 'misma', 'hay', 'han', 'hace', 'hacer', 'voy', 'vas', 'ser', 'son', 'era',
    'sin', 'mas', 'menos', 'muy', 'lo', 'le', 'se', 'su', 'sus', 'mi', 'te', 'nos',
    'and', 'the', 'for', 'with', 'not', 'pero', 'porque', 'tambien', 'nuevo', 'nueva',
    'cambio', 'cambios', 'codigo', 'quiero', 'necesito', 'tengo', 'estoy', 'vamos',
    'dos', 'tres', 'caso', 'casos', 'vez', 'sitio', 'sitios', 'parte', 'forma', 'cosa',
    'cosas', 'aqui', 'solo', 'bien', 'mal', 'siempre', 'nunca', 'antes', 'despues',
    'entonces', 'ahora', 'ver', 'dice', 'decir', 'poner', 'usar', 'uso', 'anadir',
}


def normaliza(texto: str) -> list[str]:
    t = unicodedata.normalize('NFKD', texto.lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return [p for p in re.split(r'[^a-z0-9_]+', t) if len(p) >= 3 and p not in VACIAS]


def lee_frontmatter(texto: str) -> tuple[dict, str]:
    """Lee el frontmatter YAML sin depender de PyYAML.

    Cubre el subconjunto que usa un cerebro: escalares, `[a, b]` en línea,
    bloques `>-`, y listas en bloque de mapas planos:

        comprobaciones:
          - regla: DAT-PER-1
            patron: 'findOne\\('
            mensaje: leer y después escribir es una carrera
    """
    m = RE_FRONTMATTER.match(texto)
    if not m:
        return {}, texto
    fm: dict = {}
    lineas = m.group(1).split('\n')
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        if not linea.strip() or linea.startswith('#'):
            i += 1
            continue
        if ':' not in linea or linea.startswith(' '):
            i += 1
            continue
        k, v = linea.split(':', 1)
        k, v = k.strip(), v.strip()
        if v in ('>-', '>', '|'):
            buf = []
            i += 1
            while i < len(lineas) and lineas[i].startswith('  '):
                buf.append(lineas[i].strip()); i += 1
            fm[k] = ' '.join(buf).strip()
            continue
        if v == '':
            # lista en bloque: cada `- ` abre un elemento; las líneas indentadas
            # siguientes son claves del mismo elemento
            items, actual = [], None
            i += 1
            while i < len(lineas) and (lineas[i].startswith('  ') or not lineas[i].strip()):
                l = lineas[i]
                cuerpo = l.strip()
                if cuerpo.startswith('- '):
                    actual = {}
                    items.append(actual)
                    cuerpo = cuerpo[2:].strip()
                if actual is not None and ':' in cuerpo:
                    ck, cv = cuerpo.split(':', 1)
                    actual[ck.strip()] = _escalar(cv.strip())
                elif actual is not None and cuerpo and not actual:
                    items[-1] = _escalar(cuerpo); actual = None
                i += 1
            fm[k] = items
            continue
        if v.startswith('[') and v.endswith(']'):
            fm[k] = [_escalar(x.strip()) for x in v[1:-1].split(',') if x.strip()]
        else:
            fm[k] = _escalar(v)
        i += 1
    return fm, texto[m.end():]


def _escalar(v: str):
    """Quita comillas simples o dobles envolventes."""
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    return v


def busca_raiz(desde: pathlib.Path | None = None) -> pathlib.Path:
    """Sube directorios hasta encontrar el kumiko.json. Como hace git con .git."""
    p = (desde or pathlib.Path.cwd()).resolve()
    for candidata in [p, *p.parents]:
        if (candidata / NOMBRE_CONFIG).exists():
            return candidata
    raise SystemExit(
        'No encuentro %s en esta carpeta ni en ninguna de arriba.\n'
        'Si aún no tienes cerebro, pide a Claude: «inicia un cerebro kumiko aquí».'
        % NOMBRE_CONFIG)


def _limpia(v) -> pathlib.Path | None:
    """Ignora vacíos y plantillas sin expandir como `${CLAUDE_PROJECT_DIR}`."""
    v = (str(v) if v else '').strip()
    if not v or v.startswith('${'):
        return None
    return pathlib.Path(v).expanduser()


def _puntero(d: pathlib.Path) -> pathlib.Path | None:
    """Lee un `.kumiko-cerebro`: una línea con la ruta del cerebro.

    Es lo que se usa cuando el cerebro vive en OTRO repositorio que el código.
    La ruta puede ser relativa al propio fichero, para que el repo sea movible.
    """
    f = d / '.kumiko-cerebro'
    if not f.is_file():
        return None
    destino = _limpia(f.read_text(encoding='utf-8').strip().split('\n')[0])
    if not destino:
        return None
    return destino if destino.is_absolute() else (d / destino)


def localiza(argumento=None) -> pathlib.Path:
    """Devuelve la raíz de un cerebro. Puntos de partida, en orden: el argumento,
    `KUMIKO_CEREBRO`, el directorio actual. Desde cada uno: un `.kumiko-cerebro`
    que apunte a otro sitio, y subir buscando `kumiko.json`."""
    import os as _os
    partidas = [x for x in (_limpia(argumento), _limpia(_os.environ.get('KUMIKO_CEREBRO')),
                            pathlib.Path.cwd()) if x]
    intentos, ultimo = [], None
    for d in partidas:
        p = _puntero(d)
        for candidata in ([p] if p else []) + [d]:
            intentos.append(str(candidata))
            try:
                return busca_raiz(candidata)
            except SystemExit as e:
                ultimo = e
    raise SystemExit(
        'No encuentro ningún cerebro kumiko.\n'
        'Busqué subiendo desde: %s\n\n'
        'Tres formas de decírmelo:\n'
        '  · un fichero `.kumiko-cerebro` en la raíz de tu proyecto, con la ruta dentro\n'
        '  · la variable de entorno KUMIKO_CEREBRO\n'
        '  · pasar la ruta como argumento\n\n%s' % (', '.join(intentos), ultimo or ''))


class Config:
    def __init__(self, raiz: pathlib.Path):
        self.raiz = raiz
        d = json.loads((raiz / NOMBRE_CONFIG).read_text(encoding='utf-8'))
        self.bruto = d
        self.nombre = d.get('nombre', raiz.name)
        r = d.get('rutas', {})
        self.router = r.get('router', 'CLAUDE.md')
        self.dir_reglas = r.get('reglas', 'reglas')
        self.defectos = r.get('defectos', 'aprendizajes/defectos.md')
        self.extra = r.get('extra', [])
        self.salida_indice = r.get('indice', '%s/INDICE.md' % self.dir_reglas)
        self.salida_datos = r.get('datos', '.kumiko/cerebro.json')
        self.evaluaciones = r.get('evaluaciones', 'evaluaciones/consultas.jsonl')
        self.telemetria = r.get('telemetria', '.kumiko/consultas.jsonl')
        # El harness: lo que el plugin hace solo, sin que nadie se acuerde.
        h = d.get('harness', {})
        self.harness = dict(
            inyectar_reglas=h.get('inyectar_reglas', True),      # UserPromptSubmit
            vigilar_al_editar=h.get('vigilar_al_editar', True),  # PostToolUse Edit|Write
            bloquear_commit=h.get('bloquear_commit', True),      # PreToolUse Bash(git commit)
            revisar_al_parar=h.get('revisar_al_parar', True),    # Stop
            minimo_palabras=int(h.get('minimo_palabras', 4)),
            maximo_caracteres=int(h.get('maximo_caracteres', 1800)))
        self.umbral_recall = float(d.get('evaluacion', {}).get('umbral_recall', 0.8))
        self.prefijo_nucleo = d.get('prefijo_nucleo', 'NUC')
        self.categorias = d['categorias']
        self.momentos = d['momentos']
        self.ids_categoria = {c['id'] for c in self.categorias}
        self.ids_momento = {m['id'] for m in self.momentos}
        self.nombre_categoria = {c['id']: c['nombre'] for c in self.categorias}
        self.nombre_momento = {m['id']: m['nombre'] for m in self.momentos}

    def markdown(self) -> list[pathlib.Path]:
        """Todo el markdown del cerebro, sin lo generado ni lo ajeno."""
        salida, vistos = [], set()
        carpetas = [self.dir_reglas, *self.extra, str(pathlib.PurePath(self.defectos).parent)]
        for carpeta in carpetas:
            d = self.raiz / carpeta
            if not d.is_dir():
                continue
            for p in sorted(d.rglob('*.md')):
                if 'node_modules' in str(p) or p == self.raiz / self.salida_indice:
                    continue
                if p not in vistos:
                    vistos.add(p)
                    salida.append(p)
        router = self.raiz / self.router
        if router.exists():
            salida.append(router)
        return salida


class Cerebro:
    """El cerebro cargado en memoria, listo para consultar."""

    PESOS_FICHERO = {'aplica_si': 3.0, 'senal': 2.5, 'titulo': 1.5, 'categoria': 1.0}
    PESOS_REGLA = {'titulo': 2.0, 'resumen': 1.0, 'cuerpo': 0.45}

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.ficheros: dict[str, dict] = {}
        self.reglas: dict[str, dict] = {}
        self.defectos: dict[str, dict] = {}
        self.por_fichero: dict[str, list[str]] = {}
        self._carga()
        self._indexa()

    # ---- carga --------------------------------------------------------------

    def _carga(self) -> None:
        cfg = self.cfg
        for p in cfg.markdown():
            rel = str(p.relative_to(cfg.raiz))
            texto = p.read_text(encoding='utf-8')
            fm, cuerpo = lee_frontmatter(texto)
            if rel == cfg.router:
                self._carga_nucleo(cuerpo, rel)
                continue
            if not fm.get('id'):
                continue
            fid = fm['id']
            self.ficheros[fid] = dict(
                id=fid, titulo=fm.get('titulo', fid), categoria=fm.get('categoria', ''),
                tipo=fm.get('tipo', 'regla'), momentos=fm.get('momentos', []),
                resumen=fm.get('resumen', ''), aplica_si=fm.get('aplica_si', ''),
                senal=fm.get('senal_de_incumplimiento', ''),
                evidencia=fm.get('evidencia', ''), ruta=rel,
                comprobaciones=[c for c in fm.get('comprobaciones', []) if isinstance(c, dict)],
                fuentes=[f for f in fm.get('fuentes', []) if isinstance(f, dict)])
            self.por_fichero[fid] = []
            self._carga_reglas(cuerpo, rel, fid, fm)
        self._carga_defectos()

    def _carga_reglas(self, cuerpo: str, rel: str, fid: str, fm: dict) -> None:
        marcas = sorted(list(RE_REGLA.finditer(cuerpo)) + list(RE_CHECK.finditer(cuerpo)),
                        key=lambda m: m.start())
        for i, m in enumerate(marcas):
            fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(cuerpo)
            trozo = cuerpo[m.end():fin]
            if m.re is RE_CHECK and m.group(3).strip():
                trozo = m.group(3).strip() + '\n' + trozo
            rid = m.group(1)
            self.reglas[rid] = dict(
                id=rid, titulo=m.group(2).strip().rstrip('*'),
                resumen=primera_frase(trozo, m.group(2).strip()), cuerpo=trozo,
                categoria=fm.get('categoria', ''), momentos=fm.get('momentos', []),
                tipo=fm.get('tipo', 'regla'), ruta=rel, fichero=fid)
            self.por_fichero[fid].append(rid)

    def _carga_nucleo(self, cuerpo: str, rel: str) -> None:
        pref = self.cfg.prefijo_nucleo
        marcas = list(re.finditer(r'^## (%s-\d+) · (.+)$' % re.escape(pref), cuerpo, re.M))
        if not marcas:
            return
        self.ficheros[pref] = dict(
            id=pref, titulo='Reglas de método', categoria='metodo', tipo='regla',
            momentos=[m['id'] for m in self.cfg.momentos], ruta=rel,
            resumen='Las reglas de método. Aplican siempre.',
            aplica_si='Siempre. No se negocian.', senal='', evidencia='', comprobaciones=[])
        self.por_fichero[pref] = []
        for i, m in enumerate(marcas):
            fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(cuerpo)
            trozo = cuerpo[m.end():fin]
            rid = m.group(1)
            self.reglas[rid] = dict(
                id=rid, titulo=m.group(2).strip(),
                resumen=primera_frase(trozo, m.group(2).strip()), cuerpo=trozo,
                categoria='metodo', momentos=[m2['id'] for m2 in self.cfg.momentos],
                tipo='regla', ruta=rel, fichero=pref)
            self.por_fichero[pref].append(rid)

    def _carga_defectos(self) -> None:
        p = self.cfg.raiz / self.cfg.defectos
        if not p.exists():
            return
        texto = p.read_text(encoding='utf-8')
        _, cuerpo = lee_frontmatter(texto)
        marcas = list(RE_DEFECTO.finditer(cuerpo))
        for i, m in enumerate(marcas):
            fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(cuerpo)
            did = m.group(1)
            titulo = m.group(2).strip()
            # "Previene: `DAT-PER-1`" en cualquier punto de la sección, con o sin
            # prefijo. La gente lo escribe en prosa, no en un campo.
            ref = re.search(r'[Pp]reviene:?\s*`([A-Z][\w-]*-\d+)`', cuerpo[m.end():fin])
            self.defectos[did] = dict(
                id=did, titulo=re.sub(r'\s*\([^)]*\)\s*$', '', titulo),
                etiqueta=(re.search(r'\(([^)]*)\)\s*$', titulo).group(1)
                          if re.search(r'\(([^)]*)\)\s*$', titulo) else ''),
                regla=ref.group(1) if ref else '',
                cuerpo=cuerpo[m.end():fin], ruta=self.cfg.defectos)

    # ---- índice de búsqueda -------------------------------------------------

    def _indexa(self) -> None:
        self.tok_fichero, self.tok_regla = {}, {}
        for fid, f in self.ficheros.items():
            campos = {'aplica_si': f['aplica_si'], 'senal': f['senal'], 'titulo': f['titulo'],
                      'categoria': self.cfg.nombre_categoria.get(f['categoria'], '')}
            pesos = {}
            for campo, texto in campos.items():
                for t in set(normaliza(texto)):
                    pesos[t] = max(pesos.get(t, 0.0), self.PESOS_FICHERO[campo])
            self.tok_fichero[fid] = pesos
        for rid, r in self.reglas.items():
            pesos = {}
            for campo in ('titulo', 'resumen', 'cuerpo'):
                for t in set(normaliza(r[campo])):
                    pesos[t] = max(pesos.get(t, 0.0), self.PESOS_REGLA[campo])
            self.tok_regla[rid] = pesos
        aparece: dict[str, int] = {}
        for pesos in list(self.tok_regla.values()) + list(self.tok_fichero.values()):
            for t in pesos:
                aparece[t] = aparece.get(t, 0) + 1
        n = len(self.tok_regla) + len(self.tok_fichero)
        self.idf = {t: math.log(1 + n / c) for t, c in aparece.items()}

    # El castellano declina mucho: "insertar" no es "insertarlo", "índice" no es
    # "índices". Sin esto, una consulta perfectamente razonable no encuentra nada
    # y quien lo prueba el primer día concluye que no funciona. Un prefijo común
    # de 5 letras es suficiente y sigue siendo explicable — no es un stemmer.
    MIN_PREFIJO = 5
    DESCUENTO_PARCIAL = 0.75

    def _puntua(self, pesos: dict, consulta: set) -> tuple[float, list]:
        puntos, casan = 0.0, []
        for t in consulta:
            if t in pesos:
                puntos += pesos[t] * self.idf.get(t, 1.0)
                casan.append(t)
                continue
            mejor, clave = 0.0, None
            for k, peso in pesos.items():
                if ((len(t) >= self.MIN_PREFIJO and k.startswith(t))
                        or (len(k) >= self.MIN_PREFIJO and t.startswith(k))):
                    v = peso * self.idf.get(k, 1.0) * self.DESCUENTO_PARCIAL
                    if v > mejor:
                        mejor, clave = v, k
            if clave:
                puntos += mejor
                casan.append(t + '~')        # la tilde marca que casó por prefijo
        return puntos, sorted(casan)

    def busca(self, tarea: str, momento: str | None = None, max_ficheros: int = 3):
        """[(fid, términos del tema, [(rid, términos de la regla)])].

        Dos etapas a propósito: el `aplica_si` del fichero decide *qué tema*, y el
        texto de cada regla decide *cuál dentro del tema*. Mezcladas, una palabra
        del tema puntúa igual a todas sus reglas y la explicación miente.
        """
        consulta = set(normaliza(tarea))
        if not consulta:
            return []
        candidatos = []
        for fid, ids in self.por_fichero.items():
            if momento:
                ids = [i for i in ids if momento in self.reglas[i]['momentos']]
                if not ids:
                    continue
            pf, tf = self._puntua(self.tok_fichero.get(fid, {}), consulta)
            reglas = []
            for rid in ids:
                pr, tr = self._puntua(self.tok_regla[rid], consulta)
                if pr > 0:
                    reglas.append((pr, rid, tr))
            mejor = max([p for p, _, _ in reglas], default=0.0)
            if pf + mejor > 0:
                reglas.sort(key=lambda x: (-x[0], x[1]))
                candidatos.append((pf + mejor, pf, mejor, fid, tf, reglas))
        if not candidatos:
            return []
        # Un fichero entra por una de dos puertas: o su `aplica_si` casa con la tarea,
        # o alguna de sus reglas casa de verdad. Sin esto, cualquier fichero que
        # mencione la palabra de pasada se cuela.
        tope = max(m for _, _, m, _, _, _ in candidatos)
        candidatos = [c for c in candidatos if c[1] > 0 or c[2] >= tope * 0.60]
        candidatos.sort(key=lambda x: (-x[0], x[3]))
        corte = candidatos[0][0] * 0.35
        salida = []
        for total, pf, _, fid, tf, reglas in candidatos[:max_ficheros]:
            if total < corte:
                continue
            # Las que casan por su texto van primero, con su explicación. Si además el
            # `aplica_si` del fichero ha casado (el tema es este), el resto de sus reglas
            # también aplica: se completa con ellas, en su orden, hasta cinco.
            elegidas = [(rid, tr) for _, rid, tr in reglas[:5]]
            if pf > 0 or not elegidas:
                ya = {rid for rid, _ in elegidas}
                for rid in self.por_fichero[fid]:
                    if len(elegidas) >= 5:
                        break
                    if rid not in ya:
                        elegidas.append((rid, []))
            salida.append((fid, tf, elegidas))
        return salida

    def comprobaciones(self) -> list[dict]:
        """Todas las comprobaciones ejecutables del cerebro, con su fichero."""
        salida = []
        for f in self.ficheros.values():
            for c in f.get('comprobaciones', []):
                if not c.get('patron'):
                    continue
                salida.append(dict(
                    regla=c.get('regla', f['id']), patron=c['patron'],
                    ficheros=c.get('ficheros', '**/*'),
                    mensaje=c.get('mensaje', f['senal'] or f['titulo']),
                    bloquea=str(c.get('bloquea', 'no')).lower() in ('si', 'sí', 'true', 'yes'),
                    fichero=f['id'], ruta=f['ruta']))
        return salida

    def decisiones(self) -> dict:
        """El `decisiones.json` del cerebro, si existe. Es opcional."""
        p = self.cfg.raiz / self.cfg.bruto.get('rutas', {}).get('decisiones', 'decisiones.json')
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding='utf-8'))

    def reincidencias(self, umbral: int = 2) -> list[dict]:
        """Las reglas que no están llegando.

        Una regla escrita que sale «corregido» en dos MRs distintas, o que tiene
        dos defectos detrás, no ha fallado por no existir: ha fallado por no
        encontrarse a tiempo. Este es el número que dice si el cerebro funciona;
        el número de reglas no dice nada.
        """
        corregido: dict[str, list] = {}
        for d in self.decisiones().get('decisiones', []):
            if d.get('estado') == 'corregido' and d.get('regla'):
                corregido.setdefault(d['regla'], []).append(d.get('tarea') or d.get('id'))
        defectos: dict[str, list] = {}
        for d in self.defectos.values():
            if d['regla']:
                defectos.setdefault(d['regla'], []).append(d['id'])
        salida = []
        for rid in sorted(set(corregido) | set(defectos)):
            n_c, n_d = len(set(corregido.get(rid, []))), len(defectos.get(rid, []))
            if n_c + n_d >= umbral:
                r = self.reglas.get(rid) or self.ficheros.get(rid) or {}
                salida.append(dict(
                    regla=rid, titulo=r.get('titulo', ''), categoria=r.get('categoria', ''),
                    corregido_en=sorted(set(corregido.get(rid, []))),
                    defectos=defectos.get(rid, []),
                    veces=n_c + n_d))
        salida.sort(key=lambda x: (-x['veces'], x['regla']))
        return salida

    def texto(self, id_: str) -> str:
        if id_ in self.defectos:
            d = self.defectos[id_]
            return ('## %s · %s\n%s' % (d['id'], d['titulo'], d['cuerpo'])).strip()
        r = self.reglas.get(id_)
        if not r:
            return ''
        return ('## %s · %s\n%s' % (r['id'], r['titulo'], r['cuerpo'])).strip()

    def responde(self, tarea: str, momento: str | None = None, max_ficheros: int = 3) -> str:
        aciertos = self.busca(tarea, momento, max_ficheros)
        pref = self.cfg.prefijo_nucleo
        if not aciertos:
            # un callejón sin salida es la forma más rápida de que alguien deje de
            # usar esto: si no hay acierto, al menos se enseña el mapa
            L = ['Ninguna regla casa con «%s». Prueba con los términos técnicos que vas a '
                 'tocar. Estos son los temas que tiene este cerebro:\n' % tarea.strip()]
            for f in self.ficheros.values():
                if f['aplica_si']:
                    L.append('- **`%s`** %s — _%s_' % (f['id'], f['titulo'], f['aplica_si']))
            L.append('\nLas de método (`%s-*`) aplican siempre.' % pref)
            return '\n'.join(L)
        L = ['# Reglas que aplican a: «%s»' % tarea.strip()]
        if momento:
            L.append('_Filtrado por momento: %s_' % self.cfg.nombre_momento.get(momento, momento))
        L.append('')
        ids = set()
        for fid, term_fich, reglas in aciertos:
            f = self.ficheros[fid]
            cat = self.cfg.nombre_categoria.get(f['categoria'], f['categoria'])
            L.append('## %s · %s  _(%s)_' % (fid, f['titulo'], cat))
            if term_fich:
                L.append('_El tema casa en: %s_' % ', '.join(term_fich))
            if f['senal']:
                L.append('**Se detecta por:** %s' % f['senal'])
            L.append('')
            for rid, term_regla in reglas:
                ids.add(rid)
                r = self.reglas[rid]
                L.append('- **`%s`** %s' % (rid, r['titulo']))
                L.append('  %s' % r['resumen'])
                if term_regla:
                    L.append('  _casa en: %s_' % ', '.join(term_regla))
            L.append('  ↳ texto completo: `%s`' % f['ruta'])
            L.append('')
        rel = [d for d in self.defectos.values() if d['regla'] in ids]
        if rel:
            L.append('## Ya costó caro')
            for d in rel[:5]:
                L.append('- **`%s`** %s _(previene `%s`)_' % (d['id'], d['titulo'], d['regla']))
            L.append('')
        L.append('---')
        L.append('Texto completo con `regla("<id>")` o `defecto("§NN")`. Las de método '
                 '(`%s-*`, en `%s`) aplican siempre. Antes de decir "hecho", '
                 '`checklist_entrega()`.' % (pref, self.cfg.router))
        return '\n'.join(L)


def primera_frase(trozo: str, respaldo: str) -> str:
    """Prosa de apertura de una sección: ni código, ni tabla, ni lista."""
    lineas, saltando = [], False
    for bruta in trozo.split('\n'):
        s = bruta.strip()
        if not s:
            saltando = False
            if lineas:
                break
            continue
        bloque = s.startswith(('```', '|', '>', '#', '<!--')) or re.match(r'^[-*]\s|^\d+\. ', s)
        if bloque or (saltando and bruta.startswith('  ')):
            saltando = True
            if lineas:
                break
            continue
        saltando = False
        lineas.append(s)
    if not lineas:
        return respaldo
    s = ' '.join(lineas)
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    s = re.sub(r'\[(.+?)\]\([^)]*\)', r'\1', s).replace('`', '')
    salida = ''
    for parte in re.split(r'(?<=[.:?])\s+', s):
        if salida and len(salida) + len(parte) > 150:
            break
        salida = (salida + ' ' + parte).strip()
    salida = salida or s
    if len(salida) > 190:
        return salida[:189].rstrip(' ,;') + '…'
    if salida.endswith(':'):
        return salida[:-1] + '…'
    return salida if salida.endswith(('.', '?', '…')) else salida + '…'
