---
name: iniciar-cerebro
description: Crea un cerebro de contexto kumiko desde cero en el proyecto actual, entrevistando a la persona sobre su equipo y su código. Úsala cuando pidan "inicia un cerebro", "monta kumiko aquí", "quiero un cerebro de contexto para este repo", "empezar con kumiko" o "configurar kumiko".
---

# Iniciar un cerebro

Monta un cerebro kumiko en el proyecto actual. El resultado es un `kumiko.json`, un router,
las primeras reglas y una lista de entrega — todo con contenido **real del proyecto**, no
plantillas vacías.

## Antes de preguntar nada, mira

Una entrevista con las preguntas ya medio contestadas vale diez veces más que un formulario.
Dedica los primeros minutos a leer el proyecto:

1. `README`, `CONTRIBUTING`, `docs/` — qué es el proyecto y qué convenciones declara.
2. Ficheros de reglas de agente que ya existan: `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`, `AGENTS.md`.
3. `git log --oneline -60` — busca commits del tipo *fix review comments*, *fix PR comments*,
   *hotfix*: ahí es donde vive lo que el equipo ya aprendió a la fuerza.
4. La forma del código: lenguaje, framework, cómo se manejan los errores, cómo se nombran los tests.

**Resume lo que has encontrado antes de preguntar.** Empieza por ahí, no por una hoja en blanco.

## La entrevista

Usa AskUserQuestion. Una pregunta por vez si la respuesta cambia la siguiente; agrupadas si no.
Propón siempre una opción recomendada basada en lo que has leído.

Lo que necesitas sacar, en este orden:

1. **Qué duele.** *«¿Qué te ha devuelto una MR últimamente?»* Es la pregunta más importante de
   todas: de aquí salen las primeras reglas, y son las únicas que se van a usar.
2. **Categorías.** Propón entre cuatro y siete a partir del código que has leído. `metodo`
   siempre entra. No copies la lista del ejemplo si no encaja.
3. **Momentos.** Por defecto: diseñar, escribir, revisar, entregar. Añade `desplegar` si tienen
   entornos y despliegues que dan guerra.
4. **Reglas de método.** Dos o tres, no ocho. Las que el equipo ya sabe que se salta.
5. **Un defecto real, entero.** Con evidencia: `fichero:línea` o hash de commit. Si no
   consigues uno, el cerebro nace vacío y no lo va a usar nadie — insiste una vez.

## Qué escribir

Copia la estructura de `${CLAUDE_PLUGIN_ROOT}/ejemplo/`, pero **nunca su contenido**: es un
servicio de reservas inventado y no tiene nada que ver con el proyecto de quien te lo pide.

```
kumiko.json                        configuración: rutas, categorías, momentos
CLAUDE.md                          router + reglas de método
reglas/<NN-categoria>/<NN-tema>.md ficheros de reglas con frontmatter
reglas/04-entrega/…                la lista de entrega (tipo: checklist)
aprendizajes/defectos.md           los casos reales, con su índice
evaluaciones/consultas.jsonl       consultas con respuesta conocida, para medir el enrutado
```

Las plantillas comentadas están en `${CLAUDE_PLUGIN_ROOT}/plantillas/`. La anatomía exacta de
un fichero de reglas, en `${CLAUDE_PLUGIN_ROOT}/docs/ANATOMIA.md` — **léela antes de escribir
el primero**.

Reglas al escribir:

- **Ids desde el minuto uno.** Todo encabezado de regla es `## <ID> · <título>`, y la cita y
  el ancla son el mismo string. Es lo que hace que un `grep` de una cita encuentre su definición.
- **`aplica_si` y `senal_de_incumplimiento` son lo que más importa** del frontmatter: son lo
  que el servidor MCP usa para enrutar. Escríbelas como frases, no como etiquetas.
- **Sin evidencia no entra.** Una regla sin `fichero:línea`, hash o comentario de revisión real
  detrás es una opinión. Dilo en voz alta cuando alguien te dicte una.
- Arranca con **dos o tres ficheros de reglas**, no con doce vacíos.
- **Un caso de evaluación por regla que escribas**: en `evaluaciones/consultas.jsonl`, la frase
  con la que la persona describiría la tarea (sus palabras, no las tuyas) y el id que debe
  salir. Es lo que permite tocar un `aplica_si` después sin romper nada. Plantilla en
  `${CLAUDE_PLUGIN_ROOT}/plantillas/consultas.jsonl`.

## Cerrar

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/motor/construir_indice.py
python3 ${CLAUDE_PLUGIN_ROOT}/motor/comprobar.py
python3 ${CLAUDE_PLUGIN_ROOT}/motor/evaluar.py        # el enrutado, contra las consultas que acabáis de escribir
```

Si `evaluar.py` falla en alguna consulta, arregla la frase del `aplica_si` del fichero que
debía salir (añade las palabras que usa la persona), no la consulta.

Después explica en dos frases, sin jerga:

- Cómo se consulta: describes lo que vas a tocar y te devuelve solo las reglas de eso.
- Cómo crece: cada vez que una revisión te pille algo, `/kumiko:anotar-defecto`.
- Qué hace solo: desde ahora, en cada prompt le llegan al agente las reglas que casan, cada fichero
  que escribe se vigila, y no hay commit ni «hecho» con hallazgos que bloquean. Se ve en la página
  Harness del visor.

Si la sesión la arrancó `empezar.sh`, el visor ya está abierto en el navegador y se ha ido
rellenando solo mientras escribíais: dile que lo mire. Si no, ofrécele abrirlo — es lo que hace
que se entienda de un vistazo lo que acabáis de montar — con la orden que lo hace todo:

```bash
sh ${CLAUDE_PLUGIN_ROOT}/empezar.sh <raíz del proyecto>
```

(o solo el visor: `cd ${CLAUDE_PLUGIN_ROOT}/visor && KUMIKO_CEREBRO=<raíz del cerebro> npm run dev`).

Si el cerebro ha quedado en un repositorio distinto del código, deja el puntero para que el
servidor MCP lo encuentre sin configurar nada más:

```bash
echo "<ruta al cerebro>" > .kumiko-cerebro
```

Si está en el mismo repositorio, no hace falta: el servidor sube directorios buscando el
`kumiko.json`.
