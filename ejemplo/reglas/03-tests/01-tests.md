---
id: TST
titulo: Tests
tipo: regla
categoria: tests
momentos: [escribir, revisar]
resumen: >-
  Cero literales repetidos, y el camino de error antes que el feliz.
aplica_si: >-
  Escribes o tocas cualquier test.
senal_de_incumplimiento: >-
  El mismo valor escrito en el given y en el assert; una clase de test sin ningún caso de fallo.
comprobaciones:
  - regla: TST-3
    patron: '(LocalDateTime|LocalDate|Instant)\.now\(\)'
    ficheros: 'src/**/*.kt'
    mensaje: El reloj se inyecta. now() dentro del código bajo prueba y dentro del test son dos relojes.
evidencia: reservas-api/test/CrearReservaShould.kt
---

# Tests

## TST-1 · Cero literales repetidos

Cuando el mismo valor aparece en el *given*, en el *when* y en el *assert*, el test puede
seguir pasando con el valor cambiado en un solo sitio y nadie lo ve. Todo valor va a una
constante de la clase de test.

## TST-2 · El camino de error, antes que el feliz

El happy path lo cubre cualquiera. Los que se olvidan y son los que rompen producción: la
franja solapada, la sala inexistente, el intervalo invertido, la lista vacía.

Si tu MR solo tiene tests del camino feliz, la revisión te va a pedir los otros. Escríbelos
antes.

## TST-3 · Un test que depende del reloj no prueba lo que crees

`LocalDateTime.now()` dentro del test y dentro del código bajo prueba son dos relojes
distintos, y un día se cruzan. El tiempo se inyecta. Caso real en `§2`.
