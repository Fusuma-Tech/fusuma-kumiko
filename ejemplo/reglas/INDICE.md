# Índice del cerebro · Cerebro de reservas-api (ejemplo)

> Generado por `motor/construir_indice.py`. **No lo edites a mano**: cambia la
> regla en su fichero y vuelve a ejecutarlo.

Cada regla tiene un id citable. `grep -rn "<id>" .` lleva al texto exacto.

## Por momento

| Momento | Qué leer |
|---|---|
| **Diseñar** | [`DAT-PER`](02-datos/01-persistencia.md), [`NUC`](../CLAUDE.md) |
| **Escribir** | [`ARQ-ERR`](01-arquitectura/01-errores.md), [`DAT-PER`](02-datos/01-persistencia.md), [`TST`](03-tests/01-tests.md), [`NUC`](../CLAUDE.md) |
| **Revisar** | [`ARQ-ERR`](01-arquitectura/01-errores.md), [`TST`](03-tests/01-tests.md), [`ENT`](04-entrega/01-antes-de-entregar.md), [`APR-DEF`](../aprendizajes/defectos.md), [`NUC`](../CLAUDE.md) |
| **Entregar** | [`ENT`](04-entrega/01-antes-de-entregar.md), [`APR-DEF`](../aprendizajes/defectos.md), [`NUC`](../CLAUDE.md) |

## Método

Cómo se decide y cómo se verifica.

### [`APR-DEF` · Defectos reales y su regla de prevención](../aprendizajes/defectos.md)

Cada entrada: qué se rompió, por qué, y la regla que lo evita la próxima vez.

### [`NUC` · Reglas de método](../CLAUDE.md)

**Aplica si:** Siempre. No se negocian.

| Id | Regla | Qué dice |
|---|---|---|
| `NUC-1` | Valida contra el código antes de decidir, no después | Lo que crees que hace el sistema y lo que hace divergen justo en el caso que te importa. |
| `NUC-2` | Calcula primero, publica después | Todo lo que sale del proceso —correos, colas, llamadas a otro servicio— va al final, cuando ya sabes que la operación entera es viable. Nos pasó en §2… |
| `NUC-3` | Antes de afirmar algo, compruébalo | Cuatro afirmaciones que ya han costado una vuelta de revisión, y el comando que las contesta en diez segundos. |
| `NUC-4` | Solo se toca lo nuevo | Lo que ya está en producción se queda como está. La limpieza «de paso» es un cambio propio, con su MR y sus tests. |

## Arquitectura

Errores, fronteras y contratos.

### [`ARQ-ERR` · Errores como valor](01-arquitectura/01-errores.md)

**Aplica si:** Escribes o tocas una función que puede fallar: una validación, una llamada a otro servicio, una escritura.

**Se detecta por:** Un logger.warn dentro de un catch sin propagar; una excepción usada para un caso de negocio previsto.

| Id | Regla | Qué dice |
|---|---|---|
| `ARQ-ERR-1` | Un fallo esperable se devuelve, no se lanza | Que una sala esté ocupada no es excepcional: es uno de los dos resultados normales de intentar reservarla. Va en el tipo de retorno. |
| `ARQ-ERR-2` | El fallo que solo se loguea | Es el antipatrón que más veces marca la revisión. Una función devuelve Unit, el fallo acaba en un logger.warn, y el llamante sigue como si nada. |

## Datos

Persistencia, índices y concurrencia.

### [`DAT-PER` · Persistencia y concurrencia](02-datos/01-persistencia.md)

**Aplica si:** Escribes en la base de datos, creas un índice, o compruebas si algo ya existe antes de insertarlo.

**Se detecta por:** Un SELECT seguido de un INSERT; una comprobación de duplicados en código sin restricción única detrás.

| Id | Regla | Qué dice |
|---|---|---|
| `DAT-PER-1` | Comprobar y después escribir es una condición de carrera | «¿Existe ya una reserva para esa sala y franja? No. Pues la inserto.» Entre las dos frases caben dos peticiones simultáneas, y las dos leen «no». |
| `DAT-PER-2` | La restricción única va sobre la clave de negocio completa | Una restricción sobre sala_id sola impide reservar la sala dos veces en su vida. |

## Tests

Qué se testea y qué no.

### [`TST` · Tests](03-tests/01-tests.md)

**Aplica si:** Escribes o tocas cualquier test.

**Se detecta por:** El mismo valor escrito en el given y en el assert; una clase de test sin ningún caso de fallo.

| Id | Regla | Qué dice |
|---|---|---|
| `TST-1` | Cero literales repetidos | Cuando el mismo valor aparece en el *given*, en el *when* y en el *assert*, el test puede seguir pasando con el valor cambiado en un solo sitio y nadie lo ve. |
| `TST-2` | El camino de error, antes que el feliz | El happy path lo cubre cualquiera. Los que se olvidan y son los que rompen producción… |
| `TST-3` | Un test que depende del reloj no prueba lo que crees | LocalDateTime.now() dentro del test y dentro del código bajo prueba son dos relojes distintos, y un día se cruzan. El tiempo se inyecta. |

## Entrega

Lo que se comprueba antes de decir «hecho».

### [`ENT` · Antes de entregar](04-entrega/01-antes-de-entregar.md)

**Aplica si:** Siempre, antes de decir que un cambio está terminado.

**Se detecta por:** Cualquiera de las preguntas contestada que sí sin justificación escrita.

| Id | Regla | Qué dice |
|---|---|---|
| `ENT-1` | ¿Algún fallo nuevo termina en un log sin propagarse? | Devuélvelo (ARQ-ERR-2). |
| `ENT-2` | ¿He comprobado la existencia de algo en código en vez de en la base de datos? | Si hay concurrencia posible, la restricción va en la base de datos (DAT-PER-1). |
| `ENT-3` | ¿He metido un literal repetido en un test? | A una constante (TST-1). |
| `ENT-4` | ¿Hay algún test del camino de error? | Si no, escríbelos antes de pedir revisión… |
| `ENT-5` | ¿He afirmado algo sin comprobarlo? | «Está desplegado», «ya lo teníamos», «esto no… |

## Salud del cerebro

| | |
|---|---|
| Reglas con comprobación automática | 3 de 16 |
| Reglas reincidentes | 2 |

**Reincidentes** — reglas que ya estaban escritas y volvieron a fallar. No les falta
existir: les falta llegar a tiempo. Son las primeras candidatas a una comprobación automática.

| Regla | Veces | Corregida en | Defectos |
|---|---|---|---|
| `DAT-PER-1` Comprobar y después escribir es una condición de carrera | 2 | RES-142 | `§1` |
| `NUC-2` Calcula primero, publica después | 2 | RES-158 | `§2` |

## Defectos ya pagados

Los 2 casos reales de [`aprendizajes/defectos.md`](../aprendizajes/defectos.md), con la regla que los habría evitado.

| Id | Defecto | Regla |
|---|---|---|
| `§1` | Dos reservas para la misma sala y la misma franja | `DAT-PER-1` |
| `§2` | El correo de confirmación salía antes de guardar | `NUC-2` |
