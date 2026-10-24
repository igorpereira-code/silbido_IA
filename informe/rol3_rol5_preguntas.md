# Informe: secciones de los Roles 3 y 5

> Cifras obtenidas con los módulos reales (silbido real, referencia real de piano, codificación del Rol 1 y ciclo del Rol 4). Fuente: `notebooks/rol3_rol5_motor_y_analisis.ipynb`.

## Rol 3: Operadores genéticos

**Diseño.** Todos los genes están normalizados en [0, 1]. Por eso los operadores son genéricos, y basta un recorte a [0, 1] (`reparar`) para que todo hijo sea válido. La validez, la presión selectiva y la reproducibilidad se verifican con 8 tests (`tests/test_rol3.py`).

| Tipo      | Variantes implementadas                         |
| --------- | ----------------------------------------------- |
| Selección | Torneo (k = 3), ruleta y SUS                    |
| Cruce     | Blend-α (BLX-α) y uniforme                      |
| Mutación  | Gaussiana, uniforme y no uniforme (Michalewicz) |

**Comparación de 3 combinaciones.** 5 semillas por combinación, población 30, 50 generaciones (1430 evaluaciones) y la misma población inicial para las tres.

| Combinación                                           | Fitness final (media ± desv) | Gen. al 95% de su mejora | Diversidad gen 10 | Diversidad final |
| ----------------------------------------------------- | ---------------------------- | ------------------------ | ----------------- | ---------------- |
| C3 Balance: torneo + BLX-0.5 + no uniforme            | **0.9051 ± 0.0040**          | **24**                   | 0.47              | 0.01             |
| C2 Exploración: ruleta + uniforme + mut. uniforme     | 0.9015 ± 0.0029              | 36                       | 0.73              | 0.74             |
| C1 Explotación: torneo + BLX-0.3 + gaussiana σ = 0.03 | 0.8987 ± 0.0048              | 31                       | 0.14              | 0.04             |

**Pregunta 3: explica el balance entre exploración y explotación. ¿Qué operador empuja más hacia cada lado?**

- **Explorar** es buscar en regiones nuevas del espacio. **Explotar** es refinar alrededor de las mejores soluciones conocidas. Con demasiada explotación, la población converge pronto a un óptimo local. Con demasiada exploración, el AG se parece a una búsqueda aleatoria y no afina.
- **Hacia la explotación** empujan el torneo (alta presión selectiva) y la mutación gaussiana con σ chico (pasos locales). En C1, la diversidad cae a 0.14 en la generación 10. Es la combinación que más rápido sube al inicio, pero desde la generación ~20 casi no mejora y termina **última** (0.899). Es un caso de convergencia prematura.
- **Hacia la exploración** empujan la mutación uniforme (salta a cualquier punto de [0, 1]) y la ruleta (baja presión). En C2, la diversidad se mantiene en ~0.74 hasta el final. Sube lento, pero como nunca deja de explorar, **supera a C1 hacia la generación 25**. Aun así, no afina tanto como C3.
- **Cruce:** el uniforme solo recombina valores que ya existen. El BLX-α crea valores nuevos fuera del segmento entre los padres. Cuanto mayor es α, más explora (ver `rol3_operadores_ilustracion.png`).
- **Elección: C3.** La mutación no uniforme da pasos grandes al inicio y casi nulos al final, así que pasa de explorar a explotar. Su diversidad baja de forma gradual (0.47 en la generación 10). Es la mejor durante toda la corrida y la que antes llega al 95% de su mejora (generación 24).
- **Conclusión:** explotar demasiado pronto (C1) es peor que explorar de más (C2). Lo mejor es ir de una a la otra (C3). Ver `rol3_operadores.png`.

## Rol 5: Meta-evaluación

**Robustez.** 10 corridas con semillas 0 a 9 dan un fitness final de 0.9066 ± 0.0032 (CV = 0.35%), con mínimo 0.9001 y máximo 0.9093. El resultado no depende de la suerte de una semilla.

**Pregunta 5: ¿cómo demuestras que tu AG es mejor que una búsqueda aleatoria?**

1. **Mismo presupuesto.** La búsqueda aleatoria recibe exactamente las mismas evaluaciones de fitness que el AG: 1430 por corrida. Comparar por generaciones sería injusto.
2. **Varias semillas.** 10 corridas de cada método, nunca una corrida suelta.
3. **Métricas:**
   - Fitness final: AG **0.9066** frente a **0.8850** de la búsqueda aleatoria (+2.4%).
   - Test de Mann-Whitney U unilateral: U = 100, **p = 9·10⁻⁵**. No asume normalidad.
   - **A₁₂ de Vargha-Delaney = 1.0:** en todos los pares, la corrida del AG supera a la aleatoria. El AG gana en **10 de 10** semillas.
   - **Curva de mejor fitness contra evaluaciones:** los dos métodos van parejos las primeras ~150 evaluaciones. Después la búsqueda aleatoria se estanca en ~0.88, porque mejorar al azar en 14 dimensiones es cada vez menos probable. El AG sigue subiendo porque aprovecha la información de la población.
4. **Validación auditiva (encuesta ciega, 6 personas).** Se compararon el mejor evolucionado (clip A) y Gen 0 (clip B) sin decir cuál era cuál. La pregunta del instrumento se hizo antes de que escucharan el piano real.

   | Audio              | Identificado como piano | Melodía reconocible (1–5) | Parecido al piano real (1–5) |
   | ------------------ | ----------------------- | ------------------------- | ---------------------------- |
   | Mejor evolucionado | **100%**                | 4.0                       | **2.33**                     |
   | Gen 0              | 83%                     | 4.0                       | 2.00                         |

   El mejor evolucionado gana en las dos medidas de timbre: ninguna persona lo puntuó peor que Gen 0 y una confundió Gen 0 con un órgano. Aun así, la diferencia es pequeña, por dos razones. Gen 0 ya es el mejor de 30 individuos aleatorios, y el sintetizador aditivo con ADSR suena "a piano" desde el inicio, así que la mejora numérica (0.87 → 0.91) se percibe poco. Además, ambos quedan lejos del piano real (~2/5), lo que confirma el techo del sintetizador. La melodía se reconoce igual en ambos (4/5): depende de la detección de pitch del Rol 1, no del AG.

**Sensibilidad (tornado).**

- **Hiperparámetros** (3 semillas por punto). El que más pesa es el tamaño de población: con 10 da 0.9013 y con 60 da 0.9092. Le sigue α del cruce: con 0 da 0.9008 y con 1 da 0.9081 (sin α > 0 el cruce no explora). El elitismo (0 → 0.9089, 6 → 0.9031), el parámetro b, k y pm cambian el resultado menos de 0.006. Eso es comparable a la variación entre semillas (desv ≈ 0.004), así que no se pueden considerar efectos claros.
- **Genes** (±0.2 alrededor del mejor individuo). Los más sensibles son el sostenido (hasta −0.031), la frecuencia de vibrato (−0.019), el decaimiento (−0.013) y la amplitud del 4.º armónico (−0.010). Los armónicos altos casi no influyen: en esa zona plana de la superficie hay deriva genética.

**Limitaciones del AG en este dominio.**

- El fitness máximo ronda 0.91 y no llega a 1. El sintetizador aditivo de 8 armónicos con una ADSR común no puede reproducir exactamente un piano real (martillo, inarmonicidad, decaimiento por armónico). El AG solo encuentra timbres que el sintetizador puede producir.
- Cada evaluación es cara (síntesis + STFT). Por eso el fitness se mide sobre una sola nota (la referencia es una nota real de piano), no sobre la melodía.
- El fitness en dB no equivale a la percepción humana: una mejora de 0.87 a 0.91 se nota poco al oído (encuesta: parecido 2.0 → 2.3 sobre 5).
- Si la detección de pitch falla, el AG no lo corrige, porque evoluciona el timbre y no la melodía.

**Referencias**

- Eiben, A. E., & Smith, J. E. (2015). _Introduction to Evolutionary Computing_ (2.ª ed.). Springer. Cap. 4 (operadores para representación real) y cap. 9 (evaluación experimental).
- Eshelman, L. J., & Schaffer, J. D. (1993). Real-coded genetic algorithms and interval-schemata (BLX-α). _Foundations of Genetic Algorithms 2_.
- Michalewicz, Z. (1996). _Genetic Algorithms + Data Structures = Evolution Programs_. Springer (mutación no uniforme).
- Vargha, A., & Delaney, H. D. (2000). A critique and improvement of the CL common language effect size statistics. _Journal of Educational and Behavioral Statistics_, 25(2).
