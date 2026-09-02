# Cómo funciona

## El problema

Un cerebro de contexto que crece deja de servir por una razón tonta: **la regla existe, es
correcta, y no llega al momento en que hacía falta**. No es un problema de contenido, es de
recuperación.

Las dos salidas obvias fallan las dos:

- **Cargarlo entero en el contexto.** Caro, y a partir de cierto tamaño empeora la atención
  del modelo. Además crece sin techo.
- **Confiar en que el agente lo busque.** Lo hace mal si las citas no tienen anclas, y no lo
  hace en absoluto si nada le dice que existe.

## El objetivo: no repetir lo que ya se pagó

Es tentador pensar esto como «una red neuronal que aprende de los errores». No lo es, y no
debería serlo. Una red aprende de miles de ejemplos, de forma implícita e inauditable. Un
cerebro tiene decenas de defectos —muchísimo como conocimiento, nada como datos— y su regla
fundacional es *sin evidencia no entra*. Un sistema que no puede decir **por qué** dice lo que
dice es incompatible con eso. Que el cerebro sea explícito no es una limitación: es la razón de
que se pueda confiar en él.

Lo que sí produce «no repetir» es un ciclo de tres pasos, y cada regla está en uno de tres
escalones:

| Escalón | Qué significa | Qué la sube |
|---|---|---|
| **Escrita** | existe en un fichero | nada; no evita nada por sí sola |
| **Citable** | tiene id, está enrutada, el MCP la devuelve cuando toca | `## ID · título` + `aplica_si` |
| **Comprobada** | un patrón la busca en cada commit | `comprobaciones:` + `vigilar.py` |

Y el cerebro mide dos cosas para saber si funciona: **cuántas reglas están en el tercer
escalón**, y cuántas son **reincidentes** — salieron «corregido» en más de una MR, o tienen más
de un defecto detrás. Una reincidente no ha fallado por no existir: ha fallado por no llegar a
tiempo. Es la primera candidata a una comprobación, y ese número bajando es la única prueba de
que el cerebro sirve. El número de reglas no dice nada.

### Lo que no se automatiza

El paso de capturar. Que el sistema escriba sus propias reglas a partir de su propia salida
suena bien y termina igual siempre: en tres meses un cerebro lleno de cosas plausibles que nadie
verificó, y entonces hay que verificarlo todo otra vez. Lo que sí se automatiza es el tecleo:
`anotar-defecto` lee los comentarios de la revisión y **redacta el borrador**; una persona lo
aprueba. El juicio no se delega.

## La respuesta a «encontrar»: enrutar en vez de cargar

Tres mecanismos, y ninguno es sofisticado.

### 1. Todo tiene un id, y la cita es el ancla

`## DAT-PER-1 · Comprobar y después escribir es una condición de carrera`

Un `grep -rn "DAT-PER-1"` encuentra la definición y todas las citas. Eso convierte «leer el
fichero» en «leer 40 líneas».

### 2. Cada fichero declara cuándo aplica

`aplica_si` responde *«¿me toca a mí?»* y `senal_de_incumplimiento` responde *«¿cómo se ve que
no me han seguido?»*. Son frases, no etiquetas, y son lo que se indexa para enrutar.

### 3. El índice se genera

`construir_indice.py` lee el markdown y escribe el índice y los datos. La única fuente de
verdad es el markdown; todo lo demás se deriva. Un índice escrito a mano miente en dos semanas
— pasa siempre, y `comprobar.py` está para que se note el mismo día.

## El emparejado, en dos etapas

Cuando alguien pregunta *«voy a guardar una reserva y evitar solapes»*:

1. **Qué fichero.** Se puntúan los `aplica_si` y las `senal` contra la consulta, con idf para
   que las palabras comunes no manden.
2. **Qué reglas dentro de ese fichero.** Se puntúan el título, el resumen y el cuerpo de cada
   regla.

Están separadas a propósito. Mezcladas, la palabra «mongo» puntuaba igual a las cinco reglas
del fichero de Mongo y la explicación de por qué salió cada una era falsa.

Y de ahí la propiedad que hace esto mantenible: el servidor **dice por qué eligió cada regla**.
Cuando se equivoca, se reescribe la frase del `aplica_si`. **No se toca el motor.**

Es determinista y sin embeddings a propósito. Se pierde recall con los sinónimos —se nota— y
se gana poder explicar y corregir sin reindexar nada. Si el recall llega a doler, se mide y
entonces se cambia.

## Lo que esto cuesta

Enrutar no es gratis, y conviene decirlo antes de que alguien lo descubra solo:

- **El corpus crece.** Los ids, el frontmatter y el índice generado son overhead. En un cerebro
  real medido, un **+34%**.
- **El ahorro solo existe si se lee selectivamente.** Si tu flujo es meter todo el repo en el
  contexto, esta estructura te sale más cara, no más barata.
- **El factor depende del tamaño.** En el cerebro de ejemplo, con 16 reglas, la respuesta media
  es unas 16 veces más pequeña que el corpus. En uno de 100 reglas, unas 126. Cuanto más grande
  es el cerebro, más se nota — que es exactamente cuando hace falta.

## Lo que no hace

- No valida que tus reglas sean buenas. Valida que sean **encontrables**.
- No sustituye a la revisión humana.
- No aprende solo. Un defecto entra porque alguien lo escribe.

## Ponerlo en CI

`comprobar.py` sale con código 1 si una ruta, un id o un frontmatter no cuadran, así que no
necesita envoltorio:

```yaml
# .gitlab-ci.yml
cerebro:
  image: python:3.11-slim
  script:
    - python3 motor/construir_indice.py
    - git diff --exit-code   # el índice generado tiene que estar al día en el commit
    - python3 motor/comprobar.py
```

El `git diff --exit-code` evita el fallo más común: alguien edita una regla, no regenera el
índice, y el índice empieza a mentir. Con esa línea el pipeline lo dice el mismo día en vez de
dos semanas después.

Como hook local:

```bash
echo 'python3 motor/comprobar.py' > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```
