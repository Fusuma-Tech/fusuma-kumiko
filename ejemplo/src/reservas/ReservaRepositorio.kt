package reservas

interface ReservaRepositorio {
    fun buscarPor(sala: SalaId, franja: Franja): Reserva?
    fun guardar(reserva: Reserva)

    // La versión que sí cumple DAT-PER-1: la base de datos arbitra y el
    // conflicto vuelve como resultado, no como excepción.
    fun insertar(reserva: Reserva): Resultado<ErrorDeReserva, Reserva>
}
