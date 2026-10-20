# Informe: sección del Rol 1 (borrador)

> Las cifras salen de `notebooks/rol1_codificacion.ipynb`. La sensibilidad de genes se calculó con el fitness **provisional**, decodificando con `rol1.decodificar`. Cuando exista `src/rol2_fitness.py` hay que volver a correr el notebook y actualizar esos números: el notebook usa el fitness real automáticamente. El resto (notas, codificación y espacio de búsqueda) no depende del fitness.

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

**Transposición: −24 (dos octavas).** El silbido está entre Do6 y Sol#6 (1047–1661 Hz). Con −12 la melodía quedaría en Do5–Sol#5, aguda para un piano. Con **−24** queda en **Do4–Sol#4 (262–415 Hz)**, alrededor del Do central y justo debajo de La4 = 440 Hz. La4 es la nota sobre la que el fitness compara el timbre, así que el timbre evolucionado se escucha en la zona para la que fue optimizado.

### Tamaño del espacio de búsqueda

El espacio es continuo, así que para contarlo se discretiza cada gen en *k* niveles:

| Niveles por gen | Combinaciones | Fracción que explora el AG | Tiempo para probarlas todas |
|---|---|---|---|
| 10 | 10¹⁴ | 1.4·10⁻¹¹ | 7.9·10³ años |
| **100** | **10²⁸** | **1.4·10⁻²⁵** | **7.9·10¹⁷ años** |
| 1000 | 10⁴² | 1.4·10⁻³⁹ | 7.9·10³¹ años |

Se usó el tiempo medido de 2.5 ms por evaluación. El AG del notebook final hace 30 + 50·28 = **1430 evaluaciones** por corrida. Con 100 niveles por gen, una búsqueda exhaustiva tardaría unas 56 millones de veces la edad del universo (1.4·10¹⁰ años). Por eso hace falta una búsqueda guiada como el AG. La representación ayuda en dos sentidos: usa pocos genes (14 en vez de miles de muestras) y escala cada gen según la percepción, así que el espacio que hay que buscar es el más chico posible sin perder sonidos útiles.

### Sensibilidad de genes (Día 3)

Para cada gen se recorrió su valor de 0 a 1 (21 niveles), dejando los demás fijos, en dos situaciones:
- alrededor del óptimo conocido, `codificar(GEN_REFERENCIA)`;
- desde 10 individuos aleatorios, como los de las primeras generaciones.

La sensibilidad es el rango del fitness (máx − mín) a lo largo del barrido. Se hicieron 3234 evaluaciones (`rol1_sensibilidad_genes.png`, `rol1_ranking_sensibilidad.png`).

| Gen | Sensibilidad desde fondos aleatorios | Sensibilidad alrededor del óptimo |
|---|---|---|
| `sostenido` | **0.025** | **0.021** |
| `vib_prof` | 0.012 | 0.000 |
| `liberacion` | 0.012 | 0.004 |
| `amp_h1` | 0.010 | **0.020** |
| `amp_h8` | 0.008 | 0.009 |
| `amp_h2` | 0.007 | 0.008 |
| `amp_h7` | 0.007 | 0.007 |
| `vib_frec` | 0.006 | 0.000 |
| `decaimiento` | 0.006 | 0.012 |
| `amp_h3` | 0.006 | 0.008 |
| `amp_h6` | 0.006 | 0.007 |
| `amp_h4` | 0.006 | 0.007 |
| `amp_h5` | 0.005 | 0.006 |
| `ataque` | 0.003 | **0.019** |

**Reporte al Rol 2:**
- El **sostenido** es el gen más sensible en las dos situaciones. Es la "forma" principal de la envolvente.
- **`ataque`, `amp_h1` y `decaimiento` casi no importan lejos del óptimo, pero cerca de él pesan mucho.** Sirven para el ajuste fino: el AG los afina en las últimas generaciones, cuando el resto ya está bien.
- Los **armónicos altos (h3–h8)** influyen poco y de forma pareja. Ahí la superficie de fitness es casi plana y hay riesgo de deriva genética. Esto coincide con el tornado del Rol 5.
- **Interacción entre los genes de vibrato (epistasis).** Alrededor del óptimo, `vib_frec` y `vib_prof` tienen sensibilidad 0. La razón es que, si uno vale 0, el otro no tiene efecto: el vibrato es `prof · sin(2π·frec·t)`. El efecto de un gen depende del valor de otro, así que el AG solo puede mejorar el vibrato moviendo los dos a la vez.
- El fitness provisional está comprimido entre 0.94 y 1.0, y todas las diferencias son chicas. Con el fitness real hay que volver a correr el análisis.

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
- Tiene localidad: mover un gen un poco cambia el sonido un poco, como muestran las curvas suaves de sensibilidad.
- Todo vector es válido.
- Los operadores reales del Rol 3 (BLX-α, mutación no uniforme) funcionan directamente.
- La escala log en los tiempos reparte la búsqueda según la percepción.

La evidencia está en el informe del Rol 5: con este cromosoma, el AG supera a la búsqueda aleatoria en 10 de 10 semillas (A₁₂ = 1.0) con solo 1430 evaluaciones.

### Diapositiva "Representación"

- **Título:** Representación: el cromosoma del instrumento.
- **Visual:** una barra de 14 celdas con colores por grupo: 8 armónicos (timbre), 4 ADSR (envolvente) y 2 de vibrato. Debajo, una flecha `decodificar` hacia los valores físicos (por ejemplo, ataque 0.115 → 8 ms).
- **Puntos:**
  - 14 genes reales en [0, 1], todos con significado físico. Cualquier vector es un sonido válido.
  - Tiempos en escala logarítmica: el 34 % del gen cubre los ataques percusivos (con escala lineal sería el 5.5 %).
  - Espacio de 10²⁸ combinaciones (con 100 niveles por gen). El AG lo resuelve con 1430 evaluaciones.
  - Silbido → 12 notas con pyin, más corrección de afinación (+0.21 st) y transposición de −24.
- **Figuras:** `rol1_escala_lineal_vs_log.png` y `rol1_deteccion_notas.png`.

**Referencias**
- Eiben, A. E., & Smith, J. E. (2015). *Introduction to Evolutionary Computing* (2.ª ed.). Springer. Cap. 4 (representación y operadores).
- Rothlauf, F. (2006). *Representations for Genetic and Evolutionary Algorithms* (2.ª ed.). Springer (localidad de la representación).
- Caruana, R. A., & Schaffer, J. D. (1988). Representation and hidden bias: Gray vs. binary coding for genetic algorithms. *Proc. 5th International Conference on Machine Learning*.
- Mauch, M., & Dixon, S. (2014). pYIN: A fundamental frequency estimator using probabilistic threshold distributions. *ICASSP 2014*.
