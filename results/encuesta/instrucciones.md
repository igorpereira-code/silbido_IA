# Encuesta informal (5–10 personas)

Encuesta ciega para validar de oído el resultado del AG. Los encuestados **no** deben ser del grupo ni saber qué clip es cuál.

## Archivos que se envían a cada persona

- `clip_A.wav` y `clip_B.wav`: dos versiones de la melodía (no se dice cuál es cuál).
- `results/audios/silbido.wav`: el silbido original.
- `results/audios/referencia.wav`: una nota de piano real.

## Orden (importante)

1. Escuchar **solo** `clip_A` y `clip_B` y responder para cada uno:
   - **instrumento**: ¿qué instrumento escuchas? (piano / flauta / violín / guitarra / órgano / otro)
2. Después escuchar `silbido.wav` y responder para cada clip:
   - **melodia_1a5**: ¿reconoces la melodía del silbido? 1 = nada, 5 = totalmente
3. Después escuchar `referencia.wav` (piano real) y responder para cada clip:
   - **parecido_1a5**: ¿qué tan parecido suena a ese piano? 1 = nada, 5 = igual

La pregunta del instrumento va primero para que la respuesta no dependa de haber escuchado el piano real.

## Registro

Una fila por persona y clip en `respuestas.csv`. Borrar las filas de personas que no participaron. En `instrumento`, una sola palabra en minúscula (por ejemplo `piano`).
