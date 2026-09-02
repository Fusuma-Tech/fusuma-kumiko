# Visor

Panel estático en Astro que hace legible cualquier cerebro kumiko.

```bash
python3 ../motor/construir_indice.py /ruta/a/tu/cerebro   # genera los datos
cd visor && npm install
KUMIKO_CEREBRO=/ruta/a/tu/cerebro npm run dev             # http://localhost:4321
```

Sin `KUMIKO_CEREBRO` usa el cerebro de `../ejemplo`, así que recién clonado funciona.

## Páginas

- **Resumen** — cuánto cerebro hay, dónde está el peso y cuántos ficheros declaran evidencia.
- **Reglas** — todas por categoría y momento, con buscador. La vista principal.
- **Defectos** — los casos pagados, filtrables, marcando los que no tienen regla asociada.
- **Decisiones** — solo aparece si el cerebro tiene un `decisiones.json` (ver abajo).
- **Grafo** — la red agrupada por categoría; las líneas discontinuas van del defecto a la
  regla que nació de él.

## Color

La identidad de una categoría la lleva **una marca** —un punto, un filete, un nodo— y al lado
va siempre el nombre en texto. **El texto nunca se pinta del color de su categoría.** Eso es lo
que permite usar una paleta categórica completa sobre papel sin problemas de contraste, y lo
que hace que el panel siga siendo legible en escala de grises o con daltonismo.

Los colores no están elegidos a ojo: son la paleta categórica documentada de la guía de
visualización, ocho familias en orden fijo, asignadas por posición. Validada en modo claro
sobre `#faf8f5` y en oscuro sobre `#17161a`: banda de luminosidad, suelo de croma, separación
CVD y suelo de visión normal, todo en verde.

Una categoría puede fijar el suyo en `kumiko.json`:

```json
{ "id": "datos", "nombre": "Datos", "color": "#a8365b", "colorOscuro": "#c25a78" }
```

Si lo haces, valídalo antes: los pares **adyacentes** en el orden de tus categorías son los que
tienen que distinguirse.

## Tu logo

```json
{ "marca": { "logo": "docs/logo.svg" } }
```

Ruta relativa a la raíz del cerebro. Sin ella se dibuja el nudo kumiko por defecto.

## Decisiones (opcional)

Un `decisiones.json` en la raíz del cerebro enciende la página de decisiones y las añade al
grafo:

```json
{
  "tareas": [
    { "id": "T-1", "etiqueta": "RES-142 · Reservas solapadas", "resumen": "..." }
  ],
  "decisiones": [
    {
      "id": "d-1", "tarea": "T-1",
      "etiqueta": "Restricción de exclusión en la tabla",
      "resumen": "La unicidad la impone la base de datos, no el código.",
      "regla": "DAT-PER-1",
      "estado": "corregido",
      "fuente": "revisión de Ana",
      "defecto": "§1"
    }
  ]
}
```

`estado` es `cumple`, `corregido` o `reusa`. `regla` tiene que ser un id que exista: si no, la
tarjeta lo dice en vez de callárselo.
