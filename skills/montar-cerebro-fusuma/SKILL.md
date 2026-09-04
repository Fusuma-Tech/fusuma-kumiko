---
name: montar-cerebro-fusuma
description: Monta un cerebro kumiko en un proyecto de Fusuma siguiendo el playbook acordado — invisible en git, contenido curado desde claude-mem con evidencia real, categorías por dónde duele, nodos de proceso con `fuentes:` ancladas. Úsala cuando pidan "monta un cerebro aquí", "inicia kumiko en este proyecto", "necesito el cerebro para <proyecto>" o "haz lo mismo que en finera". Complementa a `iniciar-cerebro`: esa hace la entrevista genérica del motor; esta aplica las decisiones de casa encima.
---

# Montar un cerebro, estilo Fusuma

`iniciar-cerebro` (la skill del motor) sabe montar un cerebro genérico. Esta skill añade lo que
decidimos en finera y que no queremos volver a decidir cada vez: dónde vive, de dónde sale el
contenido, y cómo se etiqueta lo que cruza sistemas. Si el proyecto no es de Fusuma o alguien
pide explícitamente el flujo genérico, usa `iniciar-cerebro` en su lugar.

## 0. Antes de nada: el entorno

```bash
python3 --version   # >= 3.10 para el servidor MCP
ls ~/.kumiko/venv 2>/dev/null || sh ${CLAUDE_PLUGIN_ROOT}/motor/instalar.sh
```

Si `claude plugin marketplace list` no enseña `kumiko`, es que este plugin no está instalado en
esta máquina: `claude plugin marketplace add <ruta o URL del fork>` y
`claude plugin install kumiko@kumiko --scope user`.

## 1. Dónde vive — invisible en git, por defecto

Salvo que te digan lo contrario, el cerebro es **de quien lo monta**, no del equipo todavía. Eso
cambia cómo se ignora:

```bash
mkdir -p cerebro
echo "./cerebro" > .kumiko-cerebro
printf '\ncerebro/\n.kumiko-cerebro\n' >> .git/info/exclude   # NO .gitignore
```

`.git/info/exclude` en vez de `.gitignore` es la decisión que importa: cero huella en el repo
compartido, nada que aparezca en un `git status` de otra persona ni que se cuele en un PR. El
día que el equipo entero lo adopte, se pasa a `.gitignore` a propósito — no antes.

Confirma con la persona si esto sigue aplicando: si el cerebro nace ya pensado para el equipo,
sáltate este paso y sigue el camino normal de kumiko (commiteado, sin puntero si vive en el
mismo repo).

## 2. Categorías: por dónde te hace daño, no por carpeta del monorepo

No copies las categorías de otro cerebro ni las saques de la estructura de carpetas. Salen de
preguntar **dónde ha dolido** en este proyecto — lee `git log` buscando *fix*, revisa Greptile en
PRs cerrados, y si hay una memoria tipo `claude-mem`, mira qué tipos de observación pesan más.

Empieza con 4-6. `metodo` entra siempre. El resto son zonas de daño reales: en finera salieron
`integraciones`, `datos`, `workflows`, `backoffice`. En otro proyecto serán otras — pregúntalo,
no lo copies.

## 3. El contenido: lote acotado, aprobado uno a uno

Nunca destiles todo el histórico de una memoria de una sentada — es el modo de fallo que la
documentación del motor señala explícitamente: en tres meses tienes un cerebro lleno de cosas
plausibles que nadie verificó.

Si hay una base de datos de memoria consultable (`claude-mem` u otra), el orden es:

1. **Filtra por señal, no por volumen.** Los tipos que ya son juicio humano curado primero
   (memorias guardadas a mano), después alerta de seguridad / crítico, después bug con ficheros
   modificados y acotado en el tiempo (último mes, no todo el histórico).
2. **Resuelve la evidencia real.** Cada candidato necesita `fichero:línea`. Si el proyecto tiene
   `graft` u otro indexador de código, úsalo para resolver el símbolo a su línea exacta — una
   memoria guarda nombres de función, no líneas. Sin evidencia verificada, el candidato no entra.
3. **Redacta el borrador con el formato de `§N`** (síntoma, causa, cómo se resolvió, regla que
   previene) y preséntalo. **La persona aprueba, corrige o descarta cada uno.** Nunca escribas
   directamente sin ese visto bueno — es la única barrera contra que el cerebro nazca con
   material que nadie comprobó.

Apunta a 15-20 candidatos en la primera pasada. Es un cerebro de arranque, no el histórico
completo.

## 4. Los nodos de proceso — lo que ningún índice de código puede ver

Si el proyecto tiene flujos que cruzan varios sistemas o apps (un workflow, un pipeline, un
proceso de negocio de varios pasos), añade una categoría `procesos` con ficheros
`tipo: contexto` — se enrutan igual que las reglas pero no se presentan como algo que cumplir.

Cada nodo se traza **contra el código real**, nunca de memoria:
- Lee el fichero que orquesta el flujo (el `.workflow.ts`, el handler, el step principal) y
  enumera la secuencia real, con los comentarios que expliquen el porqué de cada orden.
- Si hay una máquina de estados o un enum, cítalo con `fichero:línea`.
- Añade un bloque `fuentes:` en el frontmatter, uno por fichero que el nodo describe, con su
  hash actual:

  ```yaml
  fuentes:
    - ruta: apps/servicio/src/workflows/proceso/proceso.workflow.ts
      hash: <sha256 truncado a 12, con motor/fuentes.py o a mano>
  ```

  Esto es una adición del fork, no del motor original: sin `fuentes:`, un nodo de proceso
  describe una secuencia de tareas y nada avisa el día que alguien la reordene. Con él, el hook
  `PostToolUse` avisa en el acto de que ese nodo puede haber dejado de ser cierto.

## 5. Cerrar y verificar — sin esto no está terminado

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/motor/construir_indice.py
python3 ${CLAUDE_PLUGIN_ROOT}/motor/comprobar.py
python3 ${CLAUDE_PLUGIN_ROOT}/motor/evaluar.py          # necesita evaluaciones/consultas.jsonl con casos reales
python3 ${CLAUDE_PLUGIN_ROOT}/motor/prueba_humo.py "$(pwd)/cerebro"
python3 ${CLAUDE_PLUGIN_ROOT}/motor/fuentes.py --revisar   # si escribiste nodos de proceso
```

Escribe al menos un caso de `evaluaciones/consultas.jsonl` por cada regla nueva, con las
palabras que usaría la persona, no las tuyas. Si `evaluar.py` falla una consulta, se arregla el
`aplica_si` del fichero que debía salir — nunca el motor, y nunca se retoca la consulta solo para
que pase.

Objetivo antes de dar esto por terminado: **recall ≥ umbral** (0,8 por defecto) y **9/9** en la
prueba de humo.

## 6. Reportar, sin inflar

Al terminar, di en concreto:
- Cuántas reglas, en cuántos ficheros, cuántos defectos — números reales de `construir_indice.py`.
- Qué reglas salieron reincidentes sin comprobación automática (`comprobar.py` te lo dice solo):
  son las primeras candidatas a un `comprobaciones:`.
- Que hay que **reiniciar Claude Code** para que el MCP y los hooks carguen.
- Qué queda pendiente: normalmente, el espejo a Notion (fase 2) y que a las dos semanas la
  telemetría (`.kumiko/consultas.jsonl`) enseñe al menos un caso real donde una regla evitó un
  error. Si no lo enseña, el cerebro no está sirviendo y toca revisar por qué, no insistir.
