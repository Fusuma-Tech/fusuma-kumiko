# kumiko

Motor de cerebro de contexto para equipos que trabajan con agentes.

> *Kumiko* es el entramado de listones finos que sostiene un panel japonés. No es el papel:
> es la estructura que lo mantiene en su sitio. Esto tampoco es tu contenido — es lo que hace
> que se pueda encontrar.

## El problema

Tienes un `CLAUDE.md`, unas notas, o un `docs/` con convenciones. Y aun así la IA —y las
personas— se saltan reglas que estaban escritas. Casi nunca falta contenido: **la regla existe
y no llega al momento en que hacía falta.**

kumiko convierte esas notas en un cerebro consultable **por tarea**. Cada regla tiene un id
citable, cada fichero declara cuándo aplica, y un servidor MCP devuelve solo lo que toca:

```
«voy a guardar una reserva y evitar solapes»

  DAT-PER-1  Comprobar y después escribir es una condición de carrera
  DAT-PER-2  La restricción única va sobre la clave de negocio completa
  §1         Dos reservas para la misma sala y la misma franja  ← ya costó caro
```

Mil caracteres en vez del cerebro entero.

---

## 1. Pruébalo en dos minutos

Sin instalar nada. El repositorio trae un cerebro de ejemplo que funciona:

```bash
git clone <este-repo> kumiko && cd kumiko/ejemplo

python3 ../motor/servidor_mcp.py --probar "guardo una reserva y quiero evitar solapes"
python3 ../motor/servidor_mcp.py --medir
```

Y el panel:

```bash
cd ../visor && npm install && npm run dev      # http://localhost:4321
```

El ejemplo es un servicio de reserva de salas inventado, con 16 reglas y 2 defectos completos.
Sirve para ver **la forma** que tiene que tener un cerebro. Su contenido no te vale; su
estructura sí.

## 2. Instala el plugin

Los plugins de Claude Code se instalan siempre desde un marketplace, aunque sea local. Este
repositorio **es** su propio marketplace, así que basta con apuntarlo:

```
/plugin marketplace add https://gitlab.tuempresa.com/equipo/kumiko.git
/plugin install kumiko@kumiko
```

En GitLab autoalojado el `.git` final es obligatorio. Desde una copia local, la ruta a secas:

```
/plugin marketplace add /ruta/a/kumiko
/plugin install kumiko@kumiko
```

Para trastear sin instalar, cargándolo solo en esa sesión: `claude --plugin-dir /ruta/a/kumiko`.

Comprueba que ha entrado con `/skills` (salen cuatro) y `/mcp` (el servidor `kumiko`, con seis
herramientas).

**Requisitos.** Los scripts del motor valen con Python 3.9 en adelante y no necesitan nada más.
El servidor MCP, además, necesita el paquete `mcp`, que exige **Python >= 3.10** (vale 1.x o 2.x):

```sh
python3 --version                                    # si es 3.10 o más:
python3 -m pip install mcp
# En macOS el python3 del sistema es 3.9; instala uno con Homebrew:
brew install python@3.12 && python3.12 -m pip install mcp
```

No hace falta tocar nada más: el plugin arranca el servidor con `motor/lanzar_servidor.sh`, que
busca el primer Python válido (`python3.13`… `python3.10`, Homebrew, `python3`). Si el tuyo vive
en otro sitio, `export KUMIKO_PYTHON=/ruta/a/python3`.

## 3. Móntalo en tu proyecto

### Camino corto: que Claude te entreviste

En el repositorio donde programas:

> «inicia un cerebro kumiko aquí»

Claude **lee el proyecto antes de preguntar nada** — el README, las convenciones que ya tengáis
escritas, y sobre todo `git log` buscando commits de *fix review comments*, que es donde vive lo
que el equipo ya aprendió a la fuerza. Resume lo que ha encontrado y entonces te entrevista.

La primera pregunta es la que importa: **¿qué te ha devuelto una MR últimamente?** De ahí salen
las primeras reglas, y son las únicas que alguien va a usar.

Al terminar tienes un cerebro con contenido real, no plantillas vacías.

### Camino manual: cinco ficheros

Si no usas Claude Code, o prefieres entender la mecánica antes de automatizarla. Los ficheros
comentados están en [`plantillas/`](plantillas/).

**1. La configuración.** `kumiko.json` en la raíz del cerebro. Es lo único obligatorio, y lo que
marca la raíz — el motor lo busca subiendo directorios, como git con `.git`.

```jsonc
{
  "nombre": "Cerebro de mi-api",
  "categorias": [
    { "id": "metodo", "nombre": "Método", "descripcion": "Cómo se decide y cómo se verifica." },
    { "id": "datos",  "nombre": "Datos",  "descripcion": "Persistencia y concurrencia." }
  ],
  "momentos": [
    { "id": "escribir", "nombre": "Escribir" },
    { "id": "revisar",  "nombre": "Revisar" }
  ]
}
```

Empieza con **cuatro o cinco categorías**, no con doce. Salen del código que ya tienes, no de
una lista canónica.

**2. El router.** `CLAUDE.md`, con dos o tres reglas de método — las que el equipo ya sabe que
se salta:

```markdown
## NUC-1 · Valida contra el código antes de decidir

Lo que crees que hace el sistema y lo que hace divergen justo en el caso que te importa.
```

**3. Un fichero de reglas.** `reglas/01-datos/01-escrituras.md`. El frontmatter no es adorno:

```markdown
---
id: DAT
titulo: Escrituras
tipo: regla
categoria: datos
momentos: [escribir]
resumen: >-
  La unicidad la garantiza la base de datos, no tu código.
aplica_si: >-
  Escribes en la base de datos o compruebas si algo ya existe antes de insertarlo.
senal_de_incumplimiento: >-
  Un SELECT seguido de un INSERT.
evidencia: src/pedidos/CrearPedido.kt:33
---

## DAT-1 · Comprobar y después escribir es una carrera

Entre el `SELECT` y el `INSERT` caben dos peticiones. La restricción va en la tabla.
```

`aplica_si` y `senal_de_incumplimiento` son **lo que el servidor usa para enrutar**. Escríbelas
como frases con los términos que la gente usaría, no como etiquetas.

**4. El primer defecto.** `aprendizajes/defectos.md`. Es la parte que más rinde y la única que
nadie puede copiarte:

```markdown
## §1 · Dos pedidos con el mismo número (TCK-9)

**Síntoma.** Dos pedidos con número 1042.
**Causa.** `CrearPedido.kt:33` leía el máximo y sumaba uno.
**Regla.** Previene: `DAT-1`.
```

El título dice **qué se hizo mal**, no cuál fue el arreglo: dentro de seis meses nadie reconoce
su propio caso en «Añadir restricción única».

**5. Genera y comprueba.**

```bash
python3 /ruta/a/kumiko/motor/construir_indice.py
python3 /ruta/a/kumiko/motor/comprobar.py
```

Con eso ya tienes un cerebro que responde. Dos reglas y un defecto bastan para empezar; doce
ficheros vacíos no sirven para nada.

### ¿Dónde vive el cerebro?

**En el mismo repositorio que el código** si es un proyecto único: no hay nada que configurar,
el motor sube directorios hasta encontrar `kumiko.json`.

**En un repositorio aparte** si cubre varios servicios — que es lo normal en cuanto hay más de
uno. Entonces deja un puntero en la raíz de cada proyecto:

```bash
echo "../mi-cerebro" > .kumiko-cerebro
```

La ruta puede ser relativa al propio fichero, para que la copia de cada uno funcione. Si no,
está `KUMIKO_CEREBRO`. Si no encuentra ninguno, lo dice y explica las tres opciones.

## 4. El día a día

El cerebro solo sirve si crece con lo que os pasa. Cuatro momentos:

| Cuándo | Qué haces |
|---|---|
| **Antes de escribir código** | El agente llama a `reglas_para_tarea` solo. Tú describe lo que vas a tocar. |
| **Una revisión te pilla algo** | `/kumiko:anotar-defecto` ← el más valioso, y el que se olvida |
| **«esto debería ser una regla»** | `/kumiko:anadir-regla` |
| **Antes de pedir revisión** | `/kumiko:antes-de-entregar` |

Las tres skills que escriben **exigen evidencia** y paran si no la hay: un `fichero:línea`, un
hash de commit o un comentario de revisión real. *«Conviene tener cuidado con X»* no entra.

Y `anadir-regla` consulta el cerebro antes de escribir: si ya existe algo parecido, refuerza la
regla que hay en vez de crear una segunda redacción. Dos redacciones de la misma regla es como
empieza a caducar un cerebro.

Después de tocar cualquier markdown: `construir_indice.py`. El índice se genera, no se escribe.

## 5. El visor

Un panel estático que hace legible cualquier cerebro: reglas por categoría y momento con
buscador, los defectos filtrables, y un grafo donde se ve de un vistazo qué reglas tienen un
caso real detrás y cuáles no ha tocado nadie.

```bash
python3 motor/construir_indice.py /ruta/a/tu/cerebro
cd visor && npm install
KUMIKO_CEREBRO=/ruta/a/tu/cerebro npm run dev      # http://localhost:4321
```

Sin `KUMIKO_CEREBRO` muestra el de `ejemplo/`. Modo claro y oscuro, tu logo si lo quieres, y los
colores salen de tus categorías. Detalles en [`visor/README.md`](visor/README.md).

## 6. El servidor MCP

Se registra solo al instalar el plugin.

| Herramienta | Para qué |
|---|---|
| `reglas_para_tarea(tarea, momento?)` | Lo que se llama **antes** de escribir código. |
| `regla(id)` · `defecto(id)` | El texto completo de una, cuando hace falta. |
| `checklist_entrega()` | Antes de decir «hecho». |
| `buscar(texto)` | Término literal → ids donde aparece. |
| `mapa()` | Para orientarse la primera vez. |

El emparejado es determinista y sin embeddings, en dos etapas: el `aplica_si` decide **qué
tema** y el texto de cada regla decide **cuál dentro del tema**. Por eso el servidor puede
decirte *por qué* eligió cada regla — y cuando se equivoca, **se arregla la frase del
frontmatter, no el algoritmo**.

## 7. Probarlo

```bash
python3 motor/prueba_humo.py                 # sobre el cerebro de ejemplo
python3 motor/prueba_humo.py /mi/cerebro     # sobre el tuyo
```

Seis comprobaciones: que el generador escribe, que el comprobador da el cerebro por bueno, que
**detecta uno roto** —un comprobador que nunca falla no comprueba nada—, que el servidor
responde por consola, que habla MCP de verdad por stdio (`initialize`, `tools/list`,
`tools/call`) y que el visor compila.

Esa quinta es la que importa: un servidor MCP casi siempre falla en el diálogo, no en la
lógica, y no te enteras hasta que el agente dice que la herramienta no existe.

`comprobar.py` y `prueba_humo.py` salen con código 1 si algo va mal. En CI:

```yaml
cerebro:
  script:
    - python3 motor/construir_indice.py
    - git diff --exit-code       # el índice generado tiene que estar al día en el commit
    - python3 motor/comprobar.py
```

Ese `git diff --exit-code` evita el fallo más común: alguien edita una regla, no regenera el
índice, y el índice empieza a mentir.

## 8. Cuando algo no funciona

| Síntoma | Qué pasa |
|---|---|
| `/mcp` muestra kumiko con **0 herramientas** o «failed» | No hay un Python >= 3.10 con `mcp` (mira los requisitos del paso 2), o el servidor no encuentra el cerebro. `sh /ruta/a/kumiko/motor/lanzar_servidor.sh --probar "algo"` te dice cuál de las dos, y `claude --debug=mcp` enseña el log. |
| **«No encuentro ningún cerebro kumiko»** | No hay `kumiko.json` subiendo desde el proyecto. Deja un `.kumiko-cerebro` con la ruta. |
| `reglas_para_tarea` **no encuentra nada** | El `aplica_si` de tus ficheros no habla el idioma de la consulta. Reescríbelo con los términos que usaría la gente — no toques el motor. |
| Devuelve **reglas que no tocaban** | Lo mismo por el otro lado: el `aplica_si` es demasiado genérico. La respuesta te dice en qué palabras casó. |
| `comprobar.py` **falla tras editar** | Casi siempre es una cita a un id que no existe, o el índice de defectos desincronizado. El mensaje dice cuál. |
| El visor **no arranca** | Falta generar los datos: `construir_indice.py` antes que `npm run dev`. |

## 9. Qué hay aquí

```
motor/          los scripts, el núcleo compartido y el lanzador del servidor
skills/         las cuatro skills del plugin
visor/          el panel en Astro, sirve cualquier cerebro
plantillas/     los ficheros de arranque, comentados, y el hook de pre-commit
ejemplo/        un cerebro completo y ficticio: reserva de salas
docs/           ANATOMIA.md (cómo se escribe) · COMO-FUNCIONA.md (por qué así)
```

```bash
python3 motor/construir_indice.py    # genera el índice y los datos desde el markdown
python3 motor/comprobar.py           # rutas, ids, frontmatter y duplicados
python3 motor/servidor_mcp.py --probar "..."   # ver qué devolvería
python3 motor/servidor_mcp.py --medir          # coste frente a cargarlo todo
python3 motor/prueba_humo.py         # el ciclo entero
```

Python puro (3.9 o más), sin dependencias salvo `mcp` para el servidor, que pide Python >= 3.10.

## Lo que no hace

No valida que tus reglas sean buenas: valida que sean **encontrables**. No sustituye la
revisión humana. Y no aprende solo — un defecto entra porque alguien lo escribe, con evidencia.

Tampoco es gratis: los ids, el frontmatter y el índice son overhead, y en un cerebro real
medido el corpus creció un **34%**. Lo que se reduce no es el cerebro, es **la lectura** — y eso
solo se cobra si el agente lee selectivamente. Si tu contexto cabe entero, no montes nada de
esto. Los números y el razonamiento, en [`docs/COMO-FUNCIONA.md`](docs/COMO-FUNCIONA.md).
