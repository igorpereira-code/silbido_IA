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
El notebook ejecutado usa `src.rol1_codificacion` con tiempos logarítmicos y
`src.rol4_ag`. La primera celda imprime los nombres de ambos módulos para
verificar la integración.

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

## Resultados con los módulos reales (24 de octubre de 2026)

Notebook ejecutado desde cero con la codificación logarítmica del Rol 1 y el AG
real del Rol 4. Se conservaron 20 individuos, 20 generaciones, elitismo 2 y las
semillas 0, 1 y 2 para comparar ambas métricas con el mismo presupuesto.
Esta comparación del Rol 2 usa una configuración menor que la final del grupo.

| Semilla | Objetivo del AG | STFT del ganador | Croma del ganador |
| --- | --- | ---: | ---: |
| 0 | STFT | 0.8962 | 0.6825 |
| 0 | Croma | 0.8701 | 0.9764 |
| 1 | STFT | 0.8911 | 0.6030 |
| 1 | Croma | 0.8444 | 0.9783 |
| 2 | STFT | 0.8933 | 0.1837 |
| 2 | Croma | 0.8704 | 0.9779 |

Las métricas seleccionaron cromosomas distintos en las tres semillas. Optimizar
croma da valores cercanos a 0.98 en esa métrica, pero un STFT menor que al
optimizar STFT. Recomendación al Rol 4: usar STFT como objetivo principal por
su resolución de armónicos y croma como contraste. Estas puntuaciones no
demuestran por sí solas cuál audio suena mejor; hay clips comparativos.

En 100 individuos aleatorios (semilla 2026), STFT tardó 5.64 ms por evaluación
y croma 5.88 ms en este equipo, después del calentamiento. Para STFT, los
valores aleatorios fueron de 0.7261 a 0.8705 (media 0.7984). Los tiempos
dependen del equipo y del entorno de Python, y quedan por debajo del umbral
de 20 ms indicado para los experimentos.

Las 36 pruebas del repositorio pasaron con los módulos integrados. Las del
Rol 2 incluyen una referencia sintética con fitness 1, silencio con fitness 0,
validación de entradas, duración, tono, rango, reproducibilidad y uso del AG.

## Pregunta 2: superficie de fitness

Es la función que asigna una puntuación a cada punto del espacio de cromosomas.
El gráfico `results/graficos/rol2_superficie_fitness.png` es un corte de esa
superficie: varía únicamente el ataque de 0 a 1 y fija los otros trece genes.
En la corrida integrada, STFT favorece ataques cortos pero cambia poco en este
corte; croma alcanza un máximo interior cerca de 0.67 del gen normalizado.
Una superficie relativamente suave permite que mutaciones pequeñas conserven
calidad y exploren mejoras. Mesetas o picos estrechos dificultan la selección.
Un AG no necesita derivadas; tampoco se garantiza un óptimo global por suavidad.
La conversión a muestras y el umbral de bandas pueden producir discontinuidades.

## Material para diapositiva «Evaluación»

- Cromosoma → decodificación → armónicos + ADSR + vibrato → audio.
- Misma nota La4 y duración para candidato y piano real.
- STFT en dB como objetivo; croma como segunda métrica; mayor = mejor.
- Mostrar la curva del ataque y el tiempo de aproximadamente 5.6 ms/evaluación
  para STFT en este equipo.
- Reproducir `rol2_referencia.wav`, `rol2_gen0.wav` y `rol2_mejor_stft.wav`
  de `results/audios/`.

## Límites e integración actual

La codificación del Rol 1 y el AG del Rol 4 ya están integrados. Los archivos
de `results/` con prefijo `rol2_` se regeneraron con ambos módulos reales.
El AG del grupo y `final.ipynb` usan STFT como fitness principal. Este notebook
compara STFT y croma en tres semillas; sus números corresponden a una
configuración menor que la evaluación final del grupo.

Ocho armónicos con ADSR común aproximan el piano: no modelan el martillo,
inarmonicidad ni decaimiento independiente por armónico. La referencia real no
tiene un gen exacto y no se espera fitness 1. No se publica `GEN_REFERENCIA`,
para que los notebooks existentes utilicen el WAV real.

La referencia real es una sola nota La4, que permite comparar timbres con
rapidez. El mejor gen sintetiza después la melodía completa que extrajo el
Rol 1. Al mostrar audios comparativos hay que distinguir la nota real de
referencia de la melodía sintetizada.
