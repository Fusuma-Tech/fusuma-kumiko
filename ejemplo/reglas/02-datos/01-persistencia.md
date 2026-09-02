---
id: DAT-PER
titulo: Persistencia y concurrencia
tipo: regla
categoria: datos
momentos: [disenar, escribir]
resumen: >-
  Leer y después escribir es una condición de carrera. La unicidad la garantiza la base de datos, no tu código.
aplica_si: >-
  Escribes en la base de datos, creas un índice, o compruebas si algo ya existe antes de insertarlo.
senal_de_incumplimiento: >-
  Un SELECT seguido de un INSERT; una comprobación de duplicados en código sin restricción única detrás.
comprobaciones:
  - regla: DAT-PER-1
    patron: '(buscarPor|findOne|existe|findBy\w+)\([^)]*\)\s*==\s*null'
    ficheros: 'src/**/*.kt'
    mensaje: Comprobar si existe y después escribir es una carrera. La unicidad va en la base de datos.
evidencia: reservas-api/src/reservas/ReservaRepositorio.kt:78
---

# Persistencia y concurrencia

## DAT-PER-1 · Comprobar y después escribir es una condición de carrera

«¿Existe ya una reserva para esa sala y franja? No. Pues la inserto.» Entre las dos frases
caben dos peticiones simultáneas, y las dos leen «no».

```kotlin
// mal
if (repo.buscarPor(sala, franja) == null) repo.guardar(reserva)

// bien: la base de datos arbitra, y el conflicto es un resultado esperado
repo.insertar(reserva)          // viola la restricción única -> ErrorDeReserva.Solapada
```

**La regla:** cuando dos peticiones pueden competir, la unicidad la impone una **restricción
en la base de datos**, y el código trata la violación como un resultado de negocio. Caso real
en `§1`.

## DAT-PER-2 · La restricción única va sobre la clave de negocio completa

Una restricción sobre `sala_id` sola impide reservar la sala dos veces **en su vida**. Sobre
`(sala_id, inicio)` deja pasar dos reservas solapadas que empiezan en minutos distintos.

La clave de negocio de una reserva es *sala más intervalo*, y eso pide una restricción de
exclusión sobre el rango, no un índice único sobre columnas sueltas.

```sql
ALTER TABLE reservas ADD CONSTRAINT sin_solapes
  EXCLUDE USING gist (sala_id WITH =, franja WITH &&);
```

**La regla:** antes de crear la restricción, escribe en una frase qué significa «duplicado»
en este dominio. Si la frase no cabe en las columnas de tu índice, el índice está mal.
