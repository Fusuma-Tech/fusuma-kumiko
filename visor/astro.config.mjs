import { defineConfig } from 'astro/config';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Visor del cerebro. Sin integraciones: HTML, CSS y un poco de JS.
// Los datos los genera y lee src/lib/cerebro.mjs desde KUMIKO_CEREBRO.
//
// En desarrollo, además, se vigila el cerebro: cuando Claude (o tú) escribe una
// regla, anota un defecto o crea el kumiko.json de un proyecto nuevo, se
// regeneran los datos y el navegador se recarga. Así el visor va al ritmo de la
// conversación sin que nadie lance nada.

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.resolve(process.env.KUMIKO_CEREBRO || path.resolve(AQUI, '../ejemplo'));
const CEREBRO_MJS = path.resolve(AQUI, 'src/lib/cerebro.mjs');

function generados() {
  // Lo que escribe el propio generador no debe disparar otra regeneración.
  let rutas = {};
  try { rutas = JSON.parse(fs.readFileSync(path.join(RAIZ, 'kumiko.json'), 'utf8')).rutas || {}; } catch {}
  return [rutas.indice || 'INDICE.md', rutas.datos || '.kumiko/cerebro.json']
    .map((r) => path.resolve(RAIZ, r));
}

function interesa(fichero) {
  if (!fichero.startsWith(RAIZ + path.sep) && fichero !== RAIZ) return false;
  if (fichero.includes(`${path.sep}.git${path.sep}`) || fichero.includes(`${path.sep}node_modules${path.sep}`)) return false;
  if (generados().some((g) => fichero === g)) return false;
  return fichero.endsWith('.md') || fichero.endsWith('kumiko.json')
      || fichero.endsWith('decisiones.json') || fichero.endsWith('.kumiko-cerebro');
}

function vigilaCerebro() {
  return {
    name: 'kumiko-vigila-cerebro',
    configureServer(server) {
      server.watcher.add(RAIZ);
      let temporizador = null;
      const recarga = (fichero) => {
        if (!interesa(fichero)) return;
        clearTimeout(temporizador);
        temporizador = setTimeout(() => {
          const rel = path.relative(RAIZ, fichero);
          console.log(`[kumiko] cambia ${rel} → regenero y recargo`);
          const mod = server.moduleGraph.getModuleById(CEREBRO_MJS);
          // Invalidar el módulo y a quien lo importa: al volver a evaluarse,
          // cerebro.mjs regenera los datos y las páginas se pintan con ellos.
          const vistos = new Set();
          const invalida = (m) => {
            if (!m || vistos.has(m)) return;
            vistos.add(m);
            server.moduleGraph.invalidateModule(m);
            for (const imp of m.importers) invalida(imp);
          };
          invalida(mod);
          server.ws.send({ type: 'full-reload' });
        }, 400);
      };
      server.watcher.on('add', recarga);
      server.watcher.on('change', recarga);
      server.watcher.on('unlink', recarga);
      server.watcher.on('addDir', recarga);
    },
  };
}

export default defineConfig({
  site: 'http://localhost:4321',
  vite: { plugins: [vigilaCerebro()] },
});
