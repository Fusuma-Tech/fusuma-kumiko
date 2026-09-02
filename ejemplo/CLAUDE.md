# Punto de entrada — reservas-api

Este fichero **enruta**. No explica: el detalle vive en `reglas/`, indexado regla a regla en
[`reglas/INDICE.md`](reglas/INDICE.md).

> Cerebro de ejemplo. El dominio es inventado: un servicio de reserva de salas. Sirve para
> ver la **forma** que tiene que tener un cerebro, no el contenido.

## Cómo se citan las reglas

| Id | Qué es | Dónde vive |
|---|---|---|
| `NUC-3` | regla de método | este fichero |
| `ARQ-ERR-1`, `DAT-PER-2`, `TST-1` | regla de código | `reglas/<categoría>/` |
| `ENT-4` | pregunta de la lista de entrega | `reglas/04-entrega/01-antes-de-entregar.md` |
| `§1` | defecto real que ya costó caro | `aprendizajes/defectos.md` |

`grep -rn "DAT-PER-1" .` lleva al texto exacto. Cita los ids en la MR: una decisión sin id
detrás es una opinión.

---

# Las reglas de método

## NUC-1 · Valida contra el código antes de decidir, no después

Lo que crees que hace el sistema y lo que hace divergen justo en el caso que te importa.
Antes de usar un campo como discriminador, busca **todos** sus puntos de construcción, no
solo donde se consume. Antes de proponer una comprobación, mira si el código ya la responde.

## NUC-2 · Calcula primero, publica después

Todo lo que sale del proceso —correos, colas, llamadas a otro servicio— va al final, cuando
ya sabes que la operación entera es viable. Nos pasó en `§2`: el correo de confirmación salía
antes de persistir, y una reserva rechazada dejaba al cliente con un correo que mentía.

## NUC-3 · Antes de afirmar algo, compruébalo

Cuatro afirmaciones que ya han costado una vuelta de revisión, y el comando que las
contesta en diez segundos.

| Afirmación | Cómo se comprueba |
|---|---|
| «Está desplegado» | `git tag --contains <commit>` |
| «Ya lo teníamos» | `git log -S "<cadena>"` |
| «Esto no afecta a X» | busca los usos; no razones sobre el nombre de la función |
| «Está validado» | di en qué entorno y con qué datos |

## NUC-4 · Solo se toca lo nuevo

Lo que ya está en producción se queda como está. La limpieza «de paso» es un cambio propio,
con su MR y sus tests.

---

# Enrutado

| Si tu cambio toca… | Lee | Categoría |
|---|---|---|
| algo que puede fallar: validaciones, llamadas externas | [`ARQ-ERR`](reglas/01-arquitectura/01-errores.md) | arquitectura |
| la base de datos: escrituras, índices, concurrencia | [`DAT-PER`](reglas/02-datos/01-persistencia.md) | datos |
| cualquier test | [`TST`](reglas/03-tests/01-tests.md) | tests |
| **decir que está hecho** | [`ENT`](reglas/04-entrega/01-antes-de-entregar.md) | entrega |
