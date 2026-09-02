---
name: antes-de-entregar
description: Pasa el diff actual por las reglas del cerebro kumiko antes de pedir revisión o dar algo por terminado. Úsala cuando digan "revisa esto antes de subirlo", "¿está listo para MR?", "pásame el checklist", "antes de entregar" o "he terminado".
---

# Antes de entregar

Dos barridos distintos, en este orden. El primero caza lo que rompe las reglas; el segundo caza
lo que las cumple todas y aun así falla.

## 1. Barrido de cumplimiento

Primero lo mecánico, que no depende de nadie:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/motor/vigilar.py            # las comprobaciones del cerebro sobre el diff preparado
```

Cada hallazgo lleva el id de la regla. No es un defecto hasta que lo es: es un sitio donde hay
que poder explicar por qué está bien. Los que no se puedan explicar, se arreglan antes de seguir.

Después el diff propio, no la funcionalidad:

```bash
git diff --stat
git diff
```

Por cada zona que toque el diff, pregunta al cerebro qué aplica:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/motor/servidor_mcp.py --probar "<lo que toca este trozo del diff>"
```

Después recorre la lista de entrega del cerebro (el fichero con `tipo: checklist`). Son
preguntas **binarias**: se contestan sí o no, no «creo que sí». Cada «sí» sin justificación
escrita es trabajo pendiente, no un matiz.

Reporta así, y solo lo que falle:

```
ENT-2  ✗  UsuarioRepo.kt:88 comprueba existencia con find antes de insertar
          → DAT-PER-1: la unicidad va en la base de datos
ENT-4  ✗  no hay ningún test de franja solapada
```

Si no falla nada, dilo en una línea. No inventes hallazgos para parecer útil.

## 2. Barrido adversarial

El checklist no lo caza todo. Por cada paso del flujo nuevo, dos preguntas:

- **Si el proceso muere justo aquí, ¿qué estado queda?**
- **¿Qué hace el reintento con ese estado?** Si el reintento no puede arreglar nada, «dejar
  para retry» es un punto muerto disfrazado.

Y una tercera si el cambio toca dinero, reservas, cupos o cualquier recurso finito: **¿qué pasa
si dos peticiones llegan a la vez?**

## 3. Lo que no se afirma sin comprobar

Antes de escribir «listo» en la MR, verifica lo que estés a punto de afirmar:

- «Está desplegado» → `git tag --contains <commit>`
- «Ya lo teníamos» → `git log -S "<cadena>"`
- «Esto no afecta a X» → busca los usos, no razones sobre el nombre
- «Está validado» → di en qué entorno y con qué datos

## Si encuentras algo que no estaba escrito

Ese es material nuevo para el cerebro. Ofrécelo explícitamente: `/kumiko:anotar-defecto` si ya
mordió, `/kumiko:anadir-regla` si es una convención que nadie había escrito.
