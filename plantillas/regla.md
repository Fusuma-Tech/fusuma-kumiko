---
id: XXX-YYY
titulo: Tema del fichero, corto
tipo: regla
categoria: <una de las de kumiko.json>
momentos: [escribir, revisar]
resumen: >-
  Una frase. Lo que verá alguien que hojea el índice.
aplica_si: >-
  Cuándo le toca a este fichero. Escríbelo como una frase que responda "¿me toca a mí?",
  con los términos técnicos que la gente usaría. Es lo que el servidor MCP usa para enrutar.
senal_de_incumplimiento: >-
  Cómo se ve, en el código, que no se ha seguido. También se indexa: si alguien describe
  el síntoma en vez del tema, igualmente llega aquí.
evidencia: ruta/Fichero.kt:41
---

# Tema del fichero

## XXX-YYY-1 · Título de la primera regla

Una o dos frases de prosa. La primera es la que sale en el índice y en la respuesta del MCP,
así que no la desperdicies en un preámbulo.

```lenguaje
// mal
...
// bien
...
```

**La regla:** la formulación accionable, en una frase. Y el caso que la pagó, si lo hay: `§N`.

## XXX-YYY-2 · Título de la segunda

...
