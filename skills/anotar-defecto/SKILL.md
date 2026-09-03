---
name: anotar-defecto
description: Registra en el cerebro kumiko un defecto real que ya costó caro, con su evidencia y la regla que lo previene. Sabe redactar el borrador a partir de los comentarios de una revisión o de una MR. Úsala cuando digan "esto se nos ha colado", "la revisión me ha pillado esto", "apunta este fallo", "mira los comentarios de la MR", "postmortem" o "que no vuelva a pasar".
---

# Anotar un defecto

Un defecto es la unidad más valiosa del cerebro: es lo único que nadie puede copiar de un blog.
Se registra **mientras duele**, no la semana que viene — y el momento en que más duele es
también el momento en que menos ganas hay de escribirlo. Por eso esta skill hace el tecleo;
el juicio se queda con la persona.

## Si hay una revisión delante, empieza por ahí

Si la persona pega comentarios de revisión, da la URL de una MR, o tienes un conector al
repositorio con acceso a los comentarios, **no le hagas un cuestionario**: lee los comentarios
y redacta tú el borrador.

1. Lee todos los comentarios. Separa los que señalan un **defecto** (algo que estaba mal y se
   corrigió) de los que son estilo, preguntas o elogios. Solo los primeros interesan.
2. Para cada defecto, comprueba **primero contra el cerebro** si ya existe una regla que lo
   cubra: `python3 ${CLAUDE_PLUGIN_ROOT}/motor/servidor_mcp.py --probar "<el comentario>"`.
   - Si existe → esto es una **reincidencia**: la regla estaba escrita y no llegó. Dilo así,
     porque es el dato más importante del cerebro. El defecto se anota igual, citando la regla.
     Y mira la telemetría (`.kumiko/consultas.jsonl`): si la regla NO se devolvió cuando se
     trabajó en ese código, es un fallo de enrutado. Añade la frase de la tarea a
     `evaluaciones/consultas.jsonl` con esa regla como esperada, y retoca el `aplica_si` hasta
     que `motor/evaluar.py` la encuentre. Así ese fallo no se repite en silencio.
   - Si no existe → el defecto trae una regla nueva debajo del brazo (`/kumiko:anadir-regla`).
3. Lee el código que el comentario señala. **Si la explicación del revisor y el código no
   coinciden, gana el código.**
4. Redacta el borrador completo con la plantilla de abajo y **enséñaselo entero antes de
   escribir nada en el cerebro**. La persona corrige, aprueba, o descarta. Nunca escribas un
   defecto que nadie ha leído: el cerebro se pudre por ahí.

Lo que no haces: inventar el coste, inventar el `fichero:línea`, o dar por confirmado un
comentario que la MR después rebatió. Si un dato no está, pregúntalo o déjalo marcado como
`SIN CONFIRMAR`.

## Saca los cuatro campos

Pregunta lo que falte, uno por uno. No rellenes huecos por tu cuenta.

| Campo | Qué es | Cómo lo sacas |
|---|---|---|
| **Síntoma** | Qué se vio, desde fuera | *«¿Cómo os enterasteis?»* |
| **Causa** | Qué línea o decisión lo produjo | *«¿Dónde está exactamente?»* — pide `fichero:línea` |
| **Cómo se resolvió** | El arreglo, concreto | El diff o el commit |
| **Regla** | Qué lo habría evitado | *«¿Qué habría que haber hecho en su lugar?»* |

Y si lo saben, el **coste**: horas, una reunión, un cliente. Es lo que hace que la próxima
persona se lo lea.

Lee el código antes de escribir la causa. Si la persona te da una explicación y el código dice
otra cosa, gana el código — y eso mismo suele ser un segundo defecto.

## Dónde va

En el fichero de defectos que declare `kumiko.json` (por defecto `aprendizajes/defectos.md`),
al final, con el siguiente número libre. Encabezado:

```markdown
## §7 · Título que describe el error, no el arreglo (TICKET-123)
```

El título dice **qué se hizo mal**. «Comprobar y después escribir» sirve; «Añadir restricción
única» no: eso es la solución, y dentro de seis meses nadie lo reconoce como su propio caso.

Actualiza también la tabla de índice del principio del fichero: id, defecto, regla.

## Ata el defecto a su regla

Escribe en la sección `Previene: \`<ID>\`` con el id de la regla. Es lo que hace que el
servidor MCP saque el caso junto a la regla, y lo que alimenta el contador de reincidencias.

Y entonces las dos preguntas que cierran el ciclo:

- **¿Existe esa regla?** Si existe, cítala y refuérzala con este caso. Si no, esto pide una
  regla nueva → `/kumiko:anadir-regla`. Un defecto sin regla es una anécdota.
- **¿Se puede comprobar solo?** Si el incumplimiento se ve en el código con un patrón
  —`findOne` seguido de `save`, un `logger.warn` dentro de un `onFailure`, un `.now()` en el
  código bajo prueba— propón un bloque `comprobaciones:` para el frontmatter de esa regla.
  Es el paso que convierte «lo escribimos» en «no puede volver a pasar». Los patrones se
  prueban con `python3 ${CLAUDE_PLUGIN_ROOT}/motor/vigilar.py --todo` antes de darlos por buenos.

## Cerrar

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/motor/construir_indice.py
python3 ${CLAUDE_PLUGIN_ROOT}/motor/comprobar.py
```
