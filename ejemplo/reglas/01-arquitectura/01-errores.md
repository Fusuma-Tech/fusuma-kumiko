---
id: ARQ-ERR
titulo: Errores como valor
tipo: regla
categoria: arquitectura
momentos: [escribir, revisar]
resumen: >-
  Un fallo esperable se devuelve, no se lanza. Un fallo que solo se loguea es un fallo invisible.
aplica_si: >-
  Escribes o tocas una función que puede fallar: una validación, una llamada a otro servicio, una escritura.
senal_de_incumplimiento: >-
  Un logger.warn dentro de un catch sin propagar; una excepción usada para un caso de negocio previsto.
comprobaciones:
  - regla: ARQ-ERR-2
    patron: 'onFailure\s*\{[^}]*logger\.(warn|error)'
    ficheros: 'src/**/*.kt'
    mensaje: Un fallo que solo se loguea es un fallo invisible. Devuélvelo.
    bloquea: sí
evidencia: reservas-api/src/reservas/CrearReserva.kt:41
---

# Errores como valor

## ARQ-ERR-1 · Un fallo esperable se devuelve, no se lanza

Que una sala esté ocupada no es excepcional: es uno de los dos resultados normales de intentar
reservarla. Va en el tipo de retorno.

```kotlin
// mal: el llamante no puede saber que esto falla sin leer el cuerpo
fun crear(peticion: Peticion): Reserva   // lanza SalaOcupadaException

// bien: los dos resultados están en la firma
fun crear(peticion: Peticion): Resultado<ErrorDeReserva, Reserva>
```

Las excepciones se reservan para lo que **no** debería pasar nunca: una invariante rota, un
fallo de infraestructura.

## ARQ-ERR-2 · El fallo que solo se loguea

Es el antipatrón que más veces marca la revisión. Una función devuelve `Unit`, el fallo acaba
en un `logger.warn`, y el llamante sigue como si nada.

```kotlin
// antes
private fun notificar(reserva: Reserva) {
    correos.enviar(reserva).onFailure { logger.warn("no se pudo notificar: $it") }
}

// después: devuelve el fallo y el llamante decide
private fun notificar(reserva: Reserva): Resultado<ErrorDeCorreo, Unit> =
    correos.enviar(reserva)
```

**La regla:** si una operación puede fallar y el resultado importa, devuélvelo. Si decides
ignorar un fallo, el sitio donde lo ignoras lleva escrito **por qué es aceptable perderlo**.
Sin esa justificación, es un bug latente.
