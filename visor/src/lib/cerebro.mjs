// Carga el cerebro que se esté visualizando y lo prepara para las páginas.
//
// El visor no tiene datos propios: lee el `cerebro.json` que genera
// `motor/construir_indice.py`. Qué cerebro, lo dice KUMIKO_CEREBRO; si no está,
// se usa el de ejemplo, para que `npm run dev` funcione recién clonado.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const POR_DEFECTO = path.resolve(AQUI, '../../../ejemplo');

export const RAIZ = path.resolve(process.env.KUMIKO_CEREBRO || POR_DEFECTO);

function leeJson(rel, siFalta = null) {
  const p = path.join(RAIZ, rel);
  if (!fs.existsSync(p)) return siFalta;
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

const config = leeJson('kumiko.json');
if (!config) {
  throw new Error(
    `No encuentro kumiko.json en ${RAIZ}.\n` +
    `Apunta KUMIKO_CEREBRO a la raíz de tu cerebro:\n` +
    `  KUMIKO_CEREBRO=/ruta/a/tu/cerebro npm run dev`);
}

const rutaDatos = config?.rutas?.datos || '.kumiko/cerebro.json';
export const datos = leeJson(rutaDatos);
if (!datos) {
  throw new Error(
    `Falta ${rutaDatos} en ${RAIZ}.\n` +
    `Genera los datos antes de arrancar el visor:\n` +
    `  python3 motor/construir_indice.py ${RAIZ}`);
}

// ---------------------------------------------------------------------------
// Paleta categórica
//
// Ocho familias en orden fijo, asignadas por posición y nunca cicladas. No son
// valores elegidos a ojo: es la paleta documentada de la guía de visualización,
// validada en los dos modos sobre las superficies de este visor (papel #faf8f5
// y tinta #17161a). Tres de los tonos claros quedan por debajo de 3:1 sobre
// papel, así que la identidad **nunca** va solo en el color: cada marca lleva
// al lado el nombre de su categoría en texto.
//
// Una categoría puede fijar su propio color con "color" en kumiko.json. Si lo
// haces, valida los pares adyacentes antes: visor/README.md explica qué mirar.
// ---------------------------------------------------------------------------
const PALETA = [
  { claro: '#2a78d6', oscuro: '#3987e5' },   // azul
  { claro: '#eb6834', oscuro: '#d95926' },   // naranja
  { claro: '#1baf7a', oscuro: '#199e70' },   // aguamarina
  { claro: '#eda100', oscuro: '#c98500' },   // amarillo
  { claro: '#e87ba4', oscuro: '#d55181' },   // magenta
  { claro: '#008300', oscuro: '#008300' },   // verde
  { claro: '#4a3aa7', oscuro: '#9085e9' },   // violeta
  { claro: '#e34948', oscuro: '#e66767' },   // rojo
];

export const categorias = (datos.categorias || []).map((c, i) => {
  const slot = PALETA[i % PALETA.length];
  return {
    ...c,
    claro: c.color || c.colorClaro || slot.claro,
    oscuro: c.colorOscuro || c.color || slot.oscuro,
  };
});
const colorDe = Object.fromEntries(categorias.map((c) => [c.id, c]));

export const momentos = datos.momentos || [];
export const ficheros = datos.ficheros || [];
export const reglas = datos.reglas || [];
export const defectos = datos.defectos || [];
export const comprobaciones = datos.comprobaciones || [];
export const reincidencias = datos.reincidencias || [];
export const reglasComprobadas = new Set(comprobaciones.map((c) => c.regla));
export const nombre = datos.nombre || path.basename(RAIZ);
export const generado = datos.generado || '';
export const marca = config.marca || {};

export const nombreCategoria = (id) => colorDe[id]?.nombre || id;
export const nombreMomento = (id) => momentos.find((m) => m.id === id)?.nombre || id;
export const reglasDe = (fid) => reglas.filter((r) => r.fichero === fid);
export const cuentaCategoria = (id) => reglas.filter((r) => r.categoria === id).length;

/** Las variables CSS de la paleta, para inyectarlas una vez en el layout. */
export function tokensCss() {
  const claro = categorias.map((c) => `  --c-${c.id}: ${c.claro};`).join('\n');
  const oscuro = categorias.map((c) => `    --c-${c.id}: ${c.oscuro};`).join('\n');
  const clases = categorias.map((c) => `.cat-${c.id} { --cat: var(--c-${c.id}); }`).join('\n');
  return `:root {\n${claro}\n}\n@media (prefers-color-scheme: dark) {\n  :root {\n${oscuro}\n  }\n}\n${clases}\n`;
}

// ---------------------------------------------------------------------------
// Decisiones: opcional. Un cerebro puede llevar un `decisiones.json` en la raíz
// con las decisiones técnicas de cada tarea y la regla que las respalda.
// Sin él, el visor esconde esa página y el grafo enseña reglas y defectos.
// ---------------------------------------------------------------------------
export const decisiones = leeJson(config?.rutas?.decisiones || 'decisiones.json', null);
export const hayDecisiones = Boolean(decisiones?.decisiones?.length);

/** Nodos y aristas del grafo, derivados de los datos: nunca escritos a mano. */
export function grafo() {
  const nodos = new Map();
  const aristas = [];
  const anade = (n) => { if (!nodos.has(n.id)) nodos.set(n.id, n); return n.id; };

  for (const f of ficheros) {
    anade({ id: f.id, tipo: 'fichero', etiqueta: f.id, titulo: f.titulo,
            categoria: f.categoria, detalle: f.resumen || f.aplica_si, ruta: f.ruta });
    for (const r of reglasDe(f.id)) {
      anade({ id: r.id, tipo: 'regla', etiqueta: r.id, titulo: r.titulo,
              categoria: r.categoria, detalle: r.resumen, ruta: r.ruta });
      aristas.push({ de: f.id, a: r.id, tipo: 'contiene' });
    }
  }
  for (const d of defectos) {
    anade({ id: d.id, tipo: 'defecto', etiqueta: d.id, titulo: d.titulo,
            categoria: d.categoria, detalle: d.titulo, ruta: d.ruta });
    if (d.regla && nodos.has(d.regla)) aristas.push({ de: d.id, a: d.regla, tipo: 'previene' });
  }
  for (const t of decisiones?.tareas || []) {
    anade({ id: t.id, tipo: 'tarea', etiqueta: t.etiqueta || t.id, titulo: t.etiqueta || t.id,
            categoria: null, detalle: t.resumen || '' });
  }
  for (const d of decisiones?.decisiones || []) {
    const regla = nodos.get(d.regla);
    anade({ id: d.id, tipo: 'decision', etiqueta: d.etiqueta, titulo: d.etiqueta,
            categoria: regla?.categoria || null, detalle: d.resumen || '', estado: d.estado });
    if (d.tarea && nodos.has(d.tarea)) aristas.push({ de: d.tarea, a: d.id, tipo: 'contiene' });
    if (regla) aristas.push({ de: d.id, a: d.regla, tipo: d.estado || 'cumple' });
  }
  return { nodos: [...nodos.values()], aristas };
}
