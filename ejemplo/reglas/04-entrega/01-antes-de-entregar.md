---
id: ENT
titulo: Antes de entregar
tipo: checklist
categoria: entrega
momentos: [revisar, entregar]
resumen: >-
  Cinco preguntas binarias sobre el diff propio. Se contestan antes de decir "hecho".
aplica_si: >-
  Siempre, antes de decir que un cambio está terminado.
senal_de_incumplimiento: >-
  Cualquiera de las preguntas contestada que sí sin justificación escrita.
evidencia: acordado en la retro del 12/03
---

# Antes de entregar

Cinco preguntas binarias sobre **el diff propio**, no sobre la funcionalidad. Se contestan
antes de decir «hecho», no en la revisión.

1. `ENT-1` **¿Algún fallo nuevo termina en un log sin propagarse?** Devuélvelo (`ARQ-ERR-2`).
2. `ENT-2` **¿He comprobado la existencia de algo en código en vez de en la base de datos?**
   Si hay concurrencia posible, la restricción va en la base de datos (`DAT-PER-1`).
3. `ENT-3` **¿He metido un literal repetido en un test?** A una constante (`TST-1`).
4. `ENT-4` **¿Hay algún test del camino de error?** Si no, escríbelos antes de pedir revisión
   (`TST-2`).
5. `ENT-5` **¿He afirmado algo sin comprobarlo?** «Está desplegado», «ya lo teníamos», «esto no
   afecta a X» (`NUC-3`).
