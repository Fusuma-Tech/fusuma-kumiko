# Anatomía de un cerebro

Un cerebro es una carpeta con markdown y un `kumiko.json`. Nada más. El motor no guarda estado
en ningún sitio: lo que hay es lo que se lee.

## Las cuatro piezas

| Pieza | Qué es | Ejemplo |
|---|---|---|
| **router** | El punto de entrada. Enruta y guarda las reglas de método. | `CLAUDE.md` |
| **fichero de reglas** | Markdown con frontmatter. Agrupa reglas de un tema. | `reglas/02-datos/01-persistencia.md` |
| **regla** | Un encabezado con id dentro de un fichero. | `## DAT-PER-1 · …` |
| **defecto** | Un caso real que ya costó caro. | `## §1 · …` |

## El frontmatter, campo a campo

```yaml
---
id: DAT-PER                  # prefijo de las reglas de este fichero. Único en el cerebro.
titulo: Persistencia y concurrencia
tipo: regla                  # regla | checklist | contexto | aprendizaje
categoria: datos             # una de las de kumiko.json
momentos: [disenar, escribir]
resumen: >-
  Una frase para quien hojea el índice.
aplica_si: >-
  Cuándo le toca a este fichero.
senal_de_incumplimiento: >-
  Cómo se ve en el código que no se ha seguido.
evidencia: reservas-api/src/reservas/ReservaRepositorio.kt:78
---
```

`aplica_si` y `senal_de_incumplimiento` **no son documentación**: son el índice de enrutado.
Cuando el servidor devuelve una regla que no tocaba, casi siempre la respuesta es reescribir
una de esas dos frases, no tocar el motor.

`tipo` cambia cómo se trata el fichero:

- `regla` — lo normal.
- `checklist` — la lista de entrega. Es la que devuelve la herramienta `checklist_entrega`.
  Sus reglas se escriben como una lista numerada con el id en código: ``1. `ENT-1` **¿…?**``
- `contexto` — conocimiento del dominio, no reglas. Se indexa igual pero no se presenta como
  algo que cumplir.
- `aprendizaje` — el fichero de defectos.

## `comprobaciones`: cuando la regla se puede vigilar sola

Es el campo que sube una regla del segundo escalón al tercero. Declara cómo se ve el
incumplimiento **en el código**, y `motor/vigilar.py` lo busca en cada commit:

```yaml
comprobaciones:
  - regla: DAT-PER-1
    patron: '(buscarPor|findOne|findBy\w+)\([^)]*\)\s*==\s*null'
    ficheros: 'src/**/*.kt'
    mensaje: Comprobar si existe y después escribir es una carrera.
    bloquea: no
```

| Campo | Qué es |
|---|---|
| `regla` | el id que se cita en el hallazgo. Por defecto, el del fichero. |
| `patron` | expresión regular de Python, sobre cada línea. |
| `ficheros` | glob con `**`; varios separados por coma. Por defecto, todo. |
| `mensaje` | lo que lee quien lo ve. Por defecto, la `senal_de_incumplimiento`. |
| `bloquea` | `sí` corta el commit; `no` (por defecto) avisa y deja seguir. |

Dos cosas que conviene tener claras:

**No todas las reglas son comprobables, y está bien.** «Valida contra el código antes de
decidir» no se vigila con un patrón; es de juicio. Las comprobables suelen ser las de forma:
un `findOne` seguido de `save`, un `logger.warn` dentro de un `onFailure`, un `.now()` donde
el reloj debería inyectarse. Apunta a esas.

**Un hallazgo no es un defecto.** Es un sitio donde tienes que poder explicar por qué está
bien. Por eso el defecto es avisar y no cortar: si `vigilar` corta demasiado, la gente lo salta
con `--no-verify` y deja de servir. `bloquea: sí` se reserva para lo que **nunca** tiene
justificación en ese proyecto.

Los patrones se prueban antes de darlos por buenos, sobre el código real:
`python3 motor/vigilar.py --todo`.

## `fuentes`: cuando el nodo describe código que se mueve

`comprobaciones` vigila que el código cumpla la regla. `fuentes` vigila lo contrario: que la
**prosa** siga siendo verdad. Es lo que necesita un fichero `tipo: contexto`, que explica un
proceso y envejece el día que alguien reordena las tareas de un workflow:

```yaml
fuentes:
  - ruta: apps/workflows-api/src/workflows/conta/new-expense/new-expense.workflow.ts
    hash: a3f9c1d2e4b5
```

El hash es sha256 truncado a 12, y se guarda **en el markdown, no en el índice generado**. Si
viviera en el índice, regenerarlo lo actualizaría solo y el desfase no se detectaría nunca. Aquí
solo cambia cuando una persona decide que ha vuelto a leer el nodo.

| Cuándo | Qué pasa |
|---|---|
| Editas un fichero que un nodo declara como fuente | El hook `PostToolUse` te lo dice en el acto |
| `python3 motor/comprobar.py` | Lo lista como aviso, no como fallo |
| `python3 motor/fuentes.py --revisar` | El informe completo |
| Has releído el nodo y sigue siendo cierto | `python3 motor/fuentes.py --fijar <id>` |

**Un desfase no es un error.** Es un nodo que hay que releer antes de fiarse. Y `--fijar` se
ejecuta *después* de releer, nunca antes: fijar sin mirar convierte esto en un sello de goma.

## Por qué los ids

Antes de tenerlos, el texto citaba «§32» y el encabezado era `## 32.`. Un `grep "§32"`
encontraba las **citas** y nunca la **definición**, así que para resolver una referencia había
que leerse el fichero entero.

La regla es esta, y es la única que de verdad importa:

> **La cita y el ancla son el mismo string.**

De ahí sale todo lo demás: que el índice se pueda generar, que el MCP pueda devolver trozos, y
que una decisión de MR se pueda trazar hasta la regla que la respalda.

Los ids no se reciclan. Si una regla se retira, su número se queda muerto: hay MRs viejas que
lo citan.

## Convenciones que se pagan solas

- **Sin evidencia no entra.** `fichero:línea`, hash de commit o comentario de revisión real.
- **Una regla dice qué hacer, cuándo, y cómo se detecta que no se ha hecho.** «Hay que tener
  cuidado con X» no es una regla.
- **Sin duplicar.** Si la regla ya existe, refuerza la que hay con el caso nuevo.
- **El índice se genera, no se escribe.** Si lo escribes a mano, miente en dos semanas.
