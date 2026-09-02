package reservas

import java.time.LocalDateTime

// Código de ejemplo. Contiene, a propósito, los dos defectos que el cerebro
// documenta como §1 y §2, para que `vigilar.py` tenga algo que encontrar.
class CrearReserva(
    private val repo: ReservaRepositorio,
    private val correos: ServicioCorreo,
) {
    fun crear(peticion: Peticion): Reserva {
        val reserva = Reserva(peticion.sala, peticion.franja, creadaEn = LocalDateTime.now())

        // §1 · comprobar y después escribir: entre estas dos líneas caben dos peticiones
        if (repo.buscarPor(peticion.sala, peticion.franja) == null) {
            repo.guardar(reserva)
        }

        // §2 · el correo sale antes de saber si la operación entera es viable,
        // y si falla, el fallo se pierde en un log
        correos.enviar(reserva).onFailure { logger.warn("no se pudo notificar: $it") }
        return reserva
    }
}
