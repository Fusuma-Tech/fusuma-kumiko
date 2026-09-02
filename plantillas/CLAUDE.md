# Punto de entrada — <proyecto>

Este fichero **enruta**. No explica: el detalle vive en `reglas/`, indexado regla a regla en
[`reglas/INDICE.md`](reglas/INDICE.md).

## Cómo se citan las reglas

| Id | Qué es | Dónde vive |
|---|---|---|
| `NUC-1` | regla de método | este fichero |
| `XXX-YYY-1` | regla de código | `reglas/<categoría>/` |
| `ENT-1` | pregunta de la lista de entrega | `reglas/<…>/antes-de-entregar.md` |
| `§1` | defecto real que ya costó caro | `aprendizajes/defectos.md` |

`grep -rn "<id>" .` lleva al texto exacto. Cita los ids en la MR: una decisión sin id detrás
es una opinión.

---

# Las reglas de método

Dos o tres, no ocho. Las que el equipo ya sabe que se salta.

## NUC-1 · <la que más caro os sale>

...

---

# Enrutado

| Si tu cambio toca… | Lee | Categoría |
|---|---|---|
| ... | [`XXX-YYY`](reglas/…) | ... |
| **decir que está hecho** | [`ENT`](reglas/…) | entrega |
