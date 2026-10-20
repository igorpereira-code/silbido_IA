# Rol 2 - Traductor: evaluación

## Uso y alcance

`src/rol2_fitness.py` conserva las tres firmas acordadas: síntesis, fitness STFT
y fitness croma. Los notebooks existentes lo seleccionan automáticamente.
La referencia real y su procedencia están en `data/referencia.wav` y
`data/rol2_referencia.md`. No hay descargas durante la ejecución.

Para reproducir los experimentos, instalar `requirements.txt` y abrir
`notebooks/rol2_experimentos.ipynb` en Jupyter o Colab; ejecutar todas las celdas.
Para las pruebas, instalar adicionalmente pytest y ejecutar desde la raíz:

```bash
python -m pytest tests -q
```

No se modifican módulos de otros roles ni `notebooks/final.ipynb`.
Mientras falte `rol1_codificacion.py`, se usa su codificación provisional con un
aviso. Al integrarlo se usa automáticamente `rol1.decodificar`, incluida su escala
logarítmica. Los experimentos detectan igualmente el módulo real del rol 4.

## Síntesis y métricas

La síntesis suma ocho armónicos de la frecuencia MIDI, con ADSR y vibrato.
Se excluyen armónicos que alcanzarían Nyquist incluso con vibrato. La liberación
ocurre dentro de la duración de la nota; si no caben las fases ADSR, sus tiempos
se reducen proporcionalmente. Se normaliza el audio completo, sin dividir por cero.

STFT: Hann de 1024 muestras, salto 256, magnitudes relativas al máximo y piso
-80 dB. `fitness = 1 - MAE/80`. Para evitar premiar regiones silenciosas se usa
la unión de bandas que superan -60 dB en algún instante de cualquiera de los
dos audios. Incluir bandas del candidato penaliza armónicos adicionales.
Se conservan todos los instantes de esas bandas para comparar la envolvente.

Croma: agrupa potencia por clase de nota (12 clases) y calcula similitud coseno
entre matrices de croma-tiempo. Agrupa octavas, por lo que distingue peor ciertos
cambios de timbre. Ambas métricas están en [0, 1], mayor es mejor, y dan cero al
silencio. La referencia se lee y transforma una sola vez al importar el módulo.

No se usa MSE sobre muestras crudas: un desplazamiento de fase puede dar un error
grande entre sonidos de igual tono y timbre. STFT reduce esa sensibilidad, aunque
no es completamente invariante a cambios de alineación temporal.

## Evidencia inicial (20 de octubre de 2026)

Notebook ejecutado con codificación y AG provisionales, 20 individuos,
20 generaciones, elitismo 2, semillas 0, 1 y 2. No son las corridas finales del grupo.

| Semilla | Objetivo del AG | STFT del ganador | Croma del ganador |
| --- | --- | --- | --- |
| 0 | STFT | 0.8913 | 0.9121 |
| 0 | Croma | 0.8508 | 0.9624 |
| 1 | STFT | 0.8829 | 0.8080 |
| 1 | Croma | 0.8431 | 0.9793 |
| 2 | STFT | 0.8940 | 0.7134 |
| 2 | Croma | 0.8347 | 0.9787 |

Las métricas no seleccionaron el mismo cromosoma en ninguna de las tres semillas.
Recomendación al Rol 4: optimizar STFT por su resolución de armónicos y usar croma
como contraste. La tabla apoya que los objetivos difieren; no demuestra por sí
sola superioridad perceptiva. Hay audios comparativos para escucharlos.

Sobre 100 individuos aleatorios (semilla 2026), STFT tardó 2.48 ms por evaluación
y croma 2.58 ms en este equipo, después del calentamiento. STFT dio 0.7294 a
0.8514 (media 0.7916). Los tiempos dependen del equipo. No debe confundirse esta
comparación con una prueba aislada del efecto del umbral: también cambió la referencia.

Las 22 pruebas pasaron (14 casos del rol 2 y 8 del rol 3), también al cargar en
memoria la codificación real de `origin/rol1-codificacion`. Incluyen una referencia
sintética conocida con fitness 1, silencio con fitness 0, validación de entradas,
duraciones, tono, rango, reproducibilidad y uso dentro del AG existente.

## Pregunta 2: superficie de fitness

Es la función que asigna una puntuación a cada punto del espacio de cromosomas.
El gráfico `results/graficos/rol2_superficie_fitness.png` es un corte de esa
superficie: varía únicamente el ataque de 0 a 1 y fija los otros trece genes.
En esta corrida STFT favorece ataques cortos; croma alcanza un máximo interior.
Una superficie relativamente suave permite que mutaciones pequeñas conserven
calidad y exploren mejoras. Mesetas o picos estrechos dificultan la selección.
Un AG no necesita derivadas; tampoco se garantiza un óptimo global por suavidad.
La conversión a muestras y el umbral de bandas pueden producir discontinuidades.

## Material para diapositiva «Evaluación»

- Cromosoma → decodificación → armónicos + ADSR + vibrato → audio.
- Misma nota La4 y duración para candidato y piano real.
- STFT en dB como objetivo; croma como segunda métrica; mayor = mejor.
- Mostrar la curva del ataque y el tiempo de aproximadamente 2.5 ms/evaluación.
- Reproducir `rol2_referencia.wav`, `rol2_gen0.wav` y `rol2_mejor_stft.wav`
  de `results/audios/`.

## Límites e integración pendiente del grupo

Ocho armónicos con ADSR común aproximan el piano: no modelan el martillo,
inarmonicidad ni decaimiento independiente por armónico. La referencia real no
tiene un gen exacto y no se espera fitness 1. No se publica `GEN_REFERENCIA`,
para que los notebooks existentes utilicen el WAV real.

El audio real es una sola nota; en el notebook final no equivale a la melodía
completa sintetizada. Igor deberá tenerlo en cuenta al integrar la comparación.
Al integrar roles 1 y 4, repetir este notebook y los experimentos del grupo:
la codificación logarítmica cambia el paisaje en coordenadas normalizadas.
