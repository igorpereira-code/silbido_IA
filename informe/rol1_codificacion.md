# Informe: sección del Rol 1 (borrador)

> Las cifras salen de `notebooks/rol1_codificacion.ipynb`, ejecutado con los **módulos reales** de los cinco roles: el fitness del Rol 2 (STFT en dB contra una nota real de piano, `data/referencia.wav`), el AG del Rol 4 y los operadores C3 del Rol 3. El mejor individuo que usa el análisis de sensibilidad es el mismo que obtiene `final.ipynb` (semilla 42, fitness 0.9087).

## Rol 1: Representación del cromosoma

**Diseño.** Un individuo es un vector de **14 números reales en [0, 1]**. Cada posición es un parámetro físico del sintetizador aditivo. El AG solo opera sobre ese vector. La traducción a valores físicos (segundos, Hz, amplitudes) ocurre únicamente en `decodificar`, que usa el Rol 2 para sintetizar. `codificar` es su inversa exacta. El test `np.allclose(codificar(decodificar(x)), x)` pasa en 1000 vectores aleatorios y en los extremos 0 y 1.

### Tabla de genes justificada

| # | Gen | Rango | Escala | Por qué este gen | Por qué este rango |
|---|---|---|---|---|---|
| 0–7 | `amp_h1` … `amp_h8` | 0 – 1 | lineal | El timbre de un instrumento lo define sobre todo cuánta energía tiene cada armónico (múltiplos de f0). Es lo que distingue un piano de una flauta tocando la misma nota. | Son amplitudes **relativas**: el sintetizador normaliza la salida, así que solo importa la proporción entre armónicos. El 0 permite eliminar un armónico (por ejemplo, el clarinete casi no tiene armónicos pares). Con 8 armónicos y la melodía transpuesta (hasta 415 Hz), el último llega a 3.3 kHz, donde ya está casi toda la energía audible del timbre y lejos del límite de Nyquist (11 kHz). |
| 8 | `ataque` | 5 – 300 ms | **log** | Es lo primero que el oído usa para reconocer un instrumento: percutido (piano, guitarra) contra soplado o frotado (flauta, violín). | Por debajo de ~5 ms el inicio suena como un "clic". 300 ms ya es un arco de violín lento. |
| 9 | `decaimiento` | 20 ms – 1 s | **log** | Es la caída tras el golpe. En un piano es la parte más característica de la nota. | Va desde una caída casi instantánea hasta la caída lenta de una cuerda grave. |
| 10 | `sostenido` | 0 – 1 | lineal | Es el nivel al que queda la nota mientras dura. Separa los instrumentos que se apagan solos (piano ≈ 0.15) de los que se mantienen (órgano = 1). | Es una fracción del pico, así que [0, 1] cubre todos los casos. |
| 11 | `liberacion` | 20 – 500 ms | **log** | Es cómo se apaga la nota al final, y se nota en las transiciones entre notas. | Con menos de ~20 ms el corte suena como un clic. Con más de 0.5 s se encima con la nota siguiente, porque las notas del silbido duran 0.3–0.5 s. |
| 12 | `vib_frec` | 0 – 8 Hz | lineal | El vibrato es típico de la voz, el violín y la flauta, y no existe en el piano. | El vibrato natural está entre 4 y 7 Hz. El 0 permite "sin vibrato". |
| 13 | `vib_prof` | 0 – 2 % de f0 | lineal | Es cuánto oscila la afinación con el vibrato. | 2 % ≈ ±34 cents, un vibrato marcado de violín. Más que eso suena desafinado. |

**Escala logarítmica en los tiempos.** El oído percibe los tiempos de forma relativa: pasar de 5 a 10 ms se nota mucho más que pasar de 300 a 305 ms. Por eso los genes de tiempo usan `valor = mín · (máx/mín)^x`, y no la fórmula lineal `mín + x·(máx − mín)`. Esto cambia mucho cómo se reparte el gen del ataque (`rol1_escala_lineal_vs_log.png`):

| Zona del ataque | % del gen (lineal) | % del gen (logarítmica) |
|---|---|---|
| Percusivo, 5–20 ms | 5.5 % | **33.8 %** |
| Rápido, 20–50 ms | 10.0 % | 22.4 % |
| Medio, 50–120 ms | 23.4 % | 21.4 % |
| Lento, 120–300 ms | **61.2 %** | 22.4 % |

Con la escala lineal, el AG gastaría el 61 % de su búsqueda en ataques lentos que suenan casi iguales. Al mismo tiempo, la zona percusiva, que es la que necesita un piano, quedaría reducida al 5.5 % del gen. Con la escala log, cada zona perceptual recibe una parte parecida, y una mutación del mismo tamaño produce cambios audibles parecidos en todo el rango.

**Validez garantizada.** Cualquier vector en [0, 1]¹⁴ produce un sonido válido. `decodificar` además recorta a [0, 1] por seguridad. Por eso los operadores del Rol 3 no necesitan reparaciones especiales.

### Extracción de notas del silbido

La grabación (`data/silbido.wav`) es real: mono, 22050 Hz, 16 bits, 7.6 s, con la primera frase del *Himno de la alegría*. `extraer_notas` sigue los pasos del enunciado (`librosa.pyin` entre 500 y 3000 Hz, frecuencia → MIDI redondeado, agrupación de frames y regla de 80 ms). Se le agregaron tres mejoras, necesarias porque un silbido real no es una sinusoide perfecta:

1. **Filtro de confianza.** Se aceptan solo los frames con probabilidad de voz ≥ 0.5. Así se descartaron 177 de 601 frames: el ruido del primer segundo y medio y el final de la toma.
2. **Corrección de afinación.** El silbido estaba **+0.21 semitonos** por encima de la afinación estándar (La = 440 Hz), y varias notas caían casi entre dos semitonos. Al redondear, "saltaban" de una nota a otra. `librosa.pitch_tuning` mide ese desvío y se resta antes de redondear.
3. **Mediana por tramo + absorción.** Un filtro de mediana de 0.24 s, aplicado solo dentro de cada tramo con sonido, borra los temblores de afinación sin unir notas repetidas separadas por micro-silencios. Los fragmentos de menos de 80 ms pegados a una nota se suman a ella, en vez de perder su duración. Los que están aislados se descartan.

Resultado (`rol1_deteccion_notas.png`): **12 notas**, Mi Mi Fa# Sol# Sol# Fa# Mi Fa Re Re# Do Do (MIDI 84–92). La melodía es reconocible, y las notas repetidas (Mi-Mi, Sol-Sol, Do-Do) salen separadas. Dos notas aparecen partidas en dos ("Mi-Fa" y "Re-Re#") porque al silbarlas el tono fue subiendo. Es fiel a la grabación.

**Transposición: −24 (dos octavas).** El silbido está entre Do6 y Sol#6 (1047–1661 Hz). Con −12 la melodía quedaría en Do5–Sol#5, aguda para un piano. Con **−24** queda en **Do4–Sol#4 (262–415 Hz)**, alrededor del Do central y justo debajo de La4 = 440 Hz. La4 es la nota sobre la que el fitness compara el timbre, así que el timbre evolucionado se escucha en la zona para la que fue optimizado. Esta transposición es la que usa `final.ipynb`: la melodía final queda en MIDI 60–68.

### Tamaño del espacio de búsqueda

El espacio es continuo, así que para contarlo se discretiza cada gen en *k* niveles:

| Niveles por gen | Combinaciones | Fracción que explora el AG | Tiempo para probarlas todas |
|---|---|---|---|
| 10 | 10¹⁴ | 1.4·10⁻¹¹ | 1.2·10⁴ años |
| **100** | **10²⁸** | **1.4·10⁻²⁵** | **1.2·10¹⁸ años** |
| 1000 | 10⁴² | 1.4·10⁻³⁹ | 1.2·10³² años |

Se usó el tiempo medido del fitness real del Rol 2: 3.6 ms por evaluación. El AG del notebook final hace 30 + 50·28 = **1430 evaluaciones** por corrida. Con 100 niveles por gen, una búsqueda exhaustiva tardaría unas 86 millones de veces la edad del universo (1.4·10¹⁰ años). Por eso hace falta una búsqueda guiada como el AG. La representación ayuda en dos sentidos: usa pocos genes (14 en vez de miles de muestras) y escala cada gen según la percepción, así que el espacio que hay que buscar es el más chico posible sin perder sonidos útiles.

### Sensibilidad de genes (Día 3)

Para cada gen se recorrió su valor de 0 a 1 (21 niveles), dejando los demás fijos, y se midió el **fitness real del Rol 2**. Se hizo en dos situaciones:
- alrededor del **mejor evolucionado**: el mejor individuo del AG con la misma configuración y semilla que `final.ipynb` (fitness 0.9087);
- desde 10 individuos aleatorios, como los de las primeras generaciones.

La sensibilidad es el rango del fitness (máx − mín) a lo largo del barrido. Se hicieron 3234 evaluaciones (`rol1_sensibilidad_genes.png`, `rol1_ranking_sensibilidad.png`).

| Gen | Sensibilidad desde fondos aleatorios | Sensibilidad alrededor del mejor evolucionado | Valor del gen en el mejor |
|---|---|---|---|
| `sostenido` | **0.082** | **0.083** | x = 0.037 (3.7 %) |
| `ataque` | 0.032 | 0.036 | x = 0.043 (6 ms) |
| `amp_h1` | 0.030 | 0.022 | x = 1.000 |
| `vib_prof` | 0.025 | 0.015 | x = 0.847 |
| `vib_frec` | 0.021 | 0.023 | x = 0.057 (0.45 Hz) |
| `amp_h6` | 0.021 | 0.009 | x = 0.068 |
| `liberacion` | 0.020 | 0.004 | x = 0.156 (33 ms) |
| `decaimiento` | 0.017 | 0.036 | x = 0.633 (0.24 s) |
| `amp_h2` | 0.016 | 0.014 | x = 0.913 |
| `amp_h5` | 0.016 | 0.007 | x = 0.124 |
| `amp_h3` | 0.015 | 0.014 | x = 1.000 |
| `amp_h8` | 0.014 | 0.005 | x = 0.501 |
| `amp_h4` | 0.014 | 0.010 | x = 0.333 |
| `amp_h7` | 0.012 | 0.009 | x = 0.051 |

Con el fitness real, los valores van de 0.77 a 0.91. Las diferencias entre genes son mucho más claras que con el fitness provisional.

**Reporte al Rol 2:**
- El **sostenido** domina con diferencia: su sensibilidad es más del doble que la de cualquier otro gen. El mejor valor está casi en 0 (3.7 %), que es la envolvente de un piano: la nota se apaga sola después del golpe. Cuanto más sostenido, más se parece a un órgano y peor es el fitness.
- El **ataque** es el segundo gen más importante y el fitness mejora cuanto más corto es: el mejor evolucionado tiene **6 ms**, un ataque percusivo. Es justo la zona a la que la escala logarítmica le da más resolución (un tercio del gen frente al 5.5 % de la escala lineal), así que la decisión de codificación ayudó a encontrarlo.
- El **decaimiento** pesa poco lejos del mejor, pero mucho cerca de él (0.036). El fitness cae fuerte cuando supera ~0.5 s. Es un gen de ajuste fino: el AG lo afina al final, cuando el sostenido y el ataque ya están bien.
- Los **armónicos** influyen poco y de forma pareja (0.005–0.022). El más importante es el fundamental (`amp_h1`), que quedó en el máximo. En los armónicos altos la superficie es casi plana, y por eso varían mucho entre semillas (ver la deriva de genes del Rol 4).
- **Epistasis entre `sostenido` y `liberacion`.** Desde fondos aleatorios la liberación tiene una sensibilidad de 0.020, pero alrededor del mejor evolucionado casi no importa (0.004). Con un sostenido de 3.7 %, cuando llega la liberación la nota ya casi no suena, así que da igual cuánto dure. El efecto de un gen depende del valor de otro.
- **Vibrato.** El mejor tiene una frecuencia muy baja (0.45 Hz), que con notas de 0.8 s no oscila: actúa como una pequeña desafinación lenta. Un piano real no tiene vibrato, así que convendría revisar si `vib_prof` alto aporta timbre o es un artefacto de la métrica.
- Coincide con el tornado del Rol 5, que mueve cada gen ±0.2 alrededor del mejor: ahí también salen primero el sostenido, la frecuencia de vibrato y el decaimiento.

### Pregunta 1: ¿cómo influye la representación del cromosoma en la eficiencia del AG? Ejemplo de codificación mala y buena.

La representación decide qué espacio busca el AG y cómo se mueven los operadores dentro de él. Influye en la eficiencia por cuatro vías:

- **Dimensión.** Cada gen extra multiplica el tamaño del espacio (*k* niveles por gen dan *k*ⁿ combinaciones). Con menos genes relevantes, el AG encuentra buenas soluciones con menos evaluaciones.
- **Localidad.** Un cambio pequeño en el genotipo debería producir un cambio pequeño en el sonido y en el fitness. Sin localidad, la mutación y el cruce son saltos al azar, y el AG se degrada a una búsqueda aleatoria. La selección solo sirve si los hijos se parecen a sus padres.
- **Validez.** Si muchos cromosomas no representan una solución válida, se gastan evaluaciones en ellos o hacen falta reparaciones.
- **Escala.** Si el gen gasta la mayor parte de su rango en valores que suenan igual, el AG desperdicia su búsqueda ahí (ver la escala log).

**Codificación mala 1: las muestras crudas de la onda.** Una nota de 0.8 s a 22050 Hz son **17 640 genes**. Casi cualquier vector aleatorio es ruido blanco, y no hay localidad: cambiar una muestra no cambia el timbre de forma audible, y cruzar dos ondas suma fases que se cancelan. El espacio sería de 100¹⁷⁶⁴⁰ combinaciones y el AG no avanzaría.

**Codificación mala 2: binario con saltos de Hamming.** Supongamos que el ataque se codifica con 7 bits (0–127). Los valores 63 (`0111111`) y 64 (`1000000`) son vecinos, pero difieren en los 7 bits. Para pasar de uno a otro hacen falta 7 mutaciones simultáneas: es un "acantilado de Hamming". En cambio, mutar un solo bit, el más significativo, salta medio rango de golpe. Un paso pequeño en el fenotipo se vuelve imposible y un paso pequeño en el genotipo se vuelve un salto enorme: se pierde la localidad. El código Gray mitiga el problema, pero no resuelve la escala.

**Codificación buena: la usada aquí.** Son 14 parámetros físicos reales normalizados a [0, 1]:
- La dimensión es baja: 14 genes, cada uno con significado acústico.
- Tiene localidad: mover un gen un poco cambia el sonido un poco, como muestran las curvas suaves de sensibilidad con el fitness real.
- Todo vector es válido.
- Los operadores reales del Rol 3 (BLX-α, mutación no uniforme) funcionan directamente.
- La escala log en los tiempos reparte la búsqueda según la percepción.

La evidencia está en la meta-evaluación del Rol 5 con los módulos reales: con este cromosoma, el AG supera a la búsqueda aleatoria en 10 de 10 semillas (A₁₂ = 1.0, p = 9·10⁻⁵) con solo 1430 evaluaciones. Además, el ataque evolucionado (6 ms) cae justo en la zona que la escala log amplía.

### Diapositiva "Representación"

- **Título:** Representación: el cromosoma del instrumento.
- **Visual:** una barra de 14 celdas con colores por grupo: 8 armónicos (timbre), 4 ADSR (envolvente) y 2 de vibrato. Debajo, una flecha `decodificar` hacia los valores físicos (por ejemplo, el ataque del mejor evolucionado: gen 0.043 → 6 ms).
- **Puntos:**
  - 14 genes reales en [0, 1], todos con significado físico. Cualquier vector es un sonido válido.
  - Tiempos en escala logarítmica: el 34 % del gen cubre los ataques percusivos (con escala lineal sería el 5.5 %).
  - Espacio de 10²⁸ combinaciones (con 100 niveles por gen). El AG lo resuelve con 1430 evaluaciones.
  - Silbido → 12 notas con pyin, más corrección de afinación (+0.21 st) y transposición de −24.
  - Gen más sensible: el sostenido. El mejor evolucionado tiene un sostenido de 3.7 % y un ataque de 6 ms: una envolvente de piano.
- **Figuras:** `rol1_escala_lineal_vs_log.png`, `rol1_deteccion_notas.png` y, si cabe, `rol1_ranking_sensibilidad.png`.

**Referencias**
- Eiben, A. E., & Smith, J. E. (2015). *Introduction to Evolutionary Computing* (2.ª ed.). Springer. Cap. 4 (representación y operadores).
- Rothlauf, F. (2006). *Representations for Genetic and Evolutionary Algorithms* (2.ª ed.). Springer (localidad de la representación).
- Caruana, R. A., & Schaffer, J. D. (1988). Representation and hidden bias: Gray vs. binary coding for genetic algorithms. *Proc. 5th International Conference on Machine Learning*.
- Mauch, M., & Dixon, S. (2014). pYIN: A fundamental frequency estimator using probabilistic threshold distributions. *ICASSP 2014*.
