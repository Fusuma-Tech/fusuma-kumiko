---
id: APR-DEF
titulo: Defectos reales y su regla de prevención
tipo: aprendizaje
categoria: metodo
momentos: [revisar, entregar]
resumen: >-
  Cada entrada: qué se rompió, por qué, y la regla que lo evita la próxima vez.
---

# Defectos reales y su regla de prevención

Cada entrada lleva evidencia: un `fichero:línea`, un commit, o un comentario de revisión real.
**Sin evidencia no entra.** El día que este fichero contenga algo que nadie verificó, hay que
verificarlo todo otra vez.

## Índice

| Id | Defecto | Regla |
|---|---|---|
| `§1` | Dos reservas para la misma sala y la misma franja | `DAT-PER-1` |
| `§2` | El correo de confirmación salía antes de guardar | `NUC-2` |

---

## §1 · Dos reservas para la misma sala y la misma franja (RES-142)

**Síntoma.** Dos personas reservaron la sala Kioto de 10:00 a 11:00 el mismo martes. Las dos
recibieron confirmación. Se descubrió en recepción, no en los logs.

**Causa.** `CrearReserva.kt:41` comprobaba la disponibilidad con un `SELECT` y después
insertaba. Con dos peticiones en paralelo, las dos leyeron «libre». No había ninguna
restricción en la tabla: la unicidad vivía solo en ese `if`.

**Cómo se resolvió.** Restricción de exclusión sobre `(sala_id, franja)` en la tabla, y la
violación se traduce a `ErrorDeReserva.Solapada`, que ya existía y no se usaba.

**Regla.** Previene: `DAT-PER-1`. La unicidad la impone la base de datos; el código trata el
conflicto como un resultado de negocio, no como un fallo.

**Coste.** Dos días entre el aviso y el arreglo, y una reunión con oficina.

## §2 · El correo de confirmación salía antes de guardar (RES-158)

**Síntoma.** Clientes con un correo de «reserva confirmada» y ninguna reserva en el sistema.

**Causa.** `CrearReserva.kt` notificaba y después persistía. Cuando la escritura fallaba —por
la restricción nueva de `§1`, precisamente— el correo ya estaba enviado.

**Cómo se resolvió.** Se partió en dos: una función pura que valida y construye la reserva, y
la publicación de efectos al final, solo si la escritura ha ido bien.

**Regla.** Previene: `NUC-2`. Calcula primero, publica después. Un efecto externo no se lanza
hasta saber que la operación entera es viable.

**Coste.** Once correos que hubo que desmentir a mano.
