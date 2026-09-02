---
name: anadir-regla
description: Añade una regla nueva al cerebro kumiko con id, frontmatter y evidencia, o refuerza una que ya existe. Úsala cuando pidan "añade una regla", "esto debería ser una regla", "apunta esto en el cerebro" o "documenta esta convención".
---

# Añadir una regla

## Primero: comprueba que no existe ya

Dos redacciones de la misma regla es como empieza a caducar un cerebro. Antes de escribir nada:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/motor/servidor_mcp.py --probar "<la regla en una frase>"
```

Si sale algo parecido, **no crees una regla nueva**: refuerza la que hay con el caso nuevo.
Dilo claramente — «esto ya es `DAT-PER-1`, le añado tu caso» — en vez de duplicar en silencio.

## Exige evidencia

Sin evidencia no entra. Pide una de estas tres, y si no hay ninguna, dilo y para:

- un `fichero:línea` del repositorio,
- un hash de commit,
- un comentario de revisión real.

*«Conviene tener cuidado con X»* no es una regla. Una regla dice **qué hacer, cuándo, y cómo
se detecta que no se ha hecho.**

## Dónde va

Lee `kumiko.json` para saber las categorías y los momentos de este cerebro. Elige el fichero
por su `aplica_si`: si ninguno encaja, es un fichero nuevo — y entonces necesita frontmatter
completo (mira `${CLAUDE_PLUGIN_ROOT}/docs/ANATOMIA.md`).

El id sigue el prefijo del fichero y toma el siguiente número libre: `DAT-PER-3`, no
`DAT-PER-2b`. Nunca reutilices un id retirado.

## Cómo se escribe

```markdown
## DAT-PER-3 · Título en imperativo o afirmación corta

Una o dos frases de prosa que digan qué hacer y por qué. Esta primera frase es la que sale
en el índice y en la respuesta del MCP, así que hazla valer.

​```kotlin
// mal
...
// bien
...
​```

**La regla:** la formulación accionable, en una frase. Y el caso que la pagó, si lo hay: `§4`.
```

Si la regla nace de un defecto que ya está en `aprendizajes/defectos.md`, enlázalos en los dos
sentidos: la regla cita el `§N`, y el defecto dice `Previene: \`<ID>\``.

## Cerrar

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/motor/construir_indice.py
python3 ${CLAUDE_PLUGIN_ROOT}/motor/comprobar.py
```

Si `comprobar.py` falla, arréglalo antes de dar la tarea por hecha. Y enseña el id nuevo: es
lo que se va a citar en la próxima MR.
