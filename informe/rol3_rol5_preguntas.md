# Informe: secciones de los Roles 3 y 5 (borrador)

> Las cifras salen de `notebooks/rol3_rol5_motor_y_analisis.ipynb`, que por ahora corre con el fitness **provisional**. Cuando se conecten los módulos reales hay que volver a correr el notebook y actualizar estos números. El razonamiento se mantiene.

## Rol 3: Operadores genéticos

**Diseño.** Todos los genes están normalizados en [0, 1]. Por eso los operadores son genéricos, y basta un recorte a [0, 1] (`reparar`) para que todo hijo sea válido.

| Tipo | Variantes implementadas |
|---|---|
| Selección | Torneo (k = 3), ruleta y SUS |
| Cruce | Blend-α (BLX-α) y uniforme |
| Mutación | Gaussiana, uniforme y no uniforme (Michalewicz) |

**Comparación.** Se probaron 3 combinaciones con 5 semillas cada una, con población 30, 50 generaciones y la misma población inicial.

| Combinación | Fitness final (media ± desv) | Diversidad gen 10 | Diversidad final |
|---|---|---|---|
| C3 Balance: torneo + BLX-0.5 + no uniforme | **0.9968 ± 0.0023** | 0.42 | 0.02 |
| C1 Explotación: torneo + BLX-0.3 + gaussiana σ = 0.03 | 0.9932 ± 0.0019 | 0.14 | 0.04 |
| C2 Exploración: ruleta + uniforme + mutación uniforme | 0.9928 ± 0.0018 | 0.69 | 0.64 |

**Pregunta 3: explica el balance entre exploración y explotación. ¿Qué operador empuja más hacia cada lado?**

- **Explorar** es buscar en regiones nuevas del espacio. **Explotar** es refinar alrededor de las mejores soluciones conocidas. Con demasiada explotación la población converge pronto a un óptimo local. Con demasiada exploración el AG se comporta casi como una búsqueda aleatoria y nunca afina.
- **Hacia la exploración** empujan la mutación uniforme (salta a cualquier punto de [0, 1]) y la ruleta. La ruleta tiene baja presión selectiva cuando el fitness está comprimido en un rango estrecho, como pasa aquí. En C2 la diversidad se queda en alrededor de 0.64 hasta el final y el fitness no se refina.
- **Hacia la explotación** empujan el torneo (con k = 3 la probabilidad de elegir a los mejores es alta) y la mutación gaussiana con σ chico, que da pasos locales. En C1 la diversidad cae a 0.14 en apenas 10 generaciones y después la mejora es lenta: es convergencia temprana.
- El **cruce uniforme** solo recombina valores que ya existen en la población. El **BLX-α** crea valores nuevos fuera del segmento entre los padres, y esa zona se amplía cuanto mayor es α (ver `rol3_operadores_ilustracion.png`). En el tornado, α = 0 da 0.9931 y α = 1 da 0.9973.
- **Elección: C3.** La mutación no uniforme explora al inicio (pasos grandes) y explota al final (pasos que tienden a 0). La diversidad baja de forma gradual (0.42 en la generación 10) y C3 logra el mejor fitness final. Ver `rol3_operadores.png`.

## Rol 5: Meta-evaluación

**Robustez.** Se hicieron 10 corridas con semillas 0 a 9. Fitness final 0.99683 ± 0.00178 (CV = 0.18%), con mínimo 0.9931 y máximo 0.9988. El resultado no depende de la suerte de una semilla.

**Pregunta 5: ¿cómo demuestras que tu AG es mejor que una búsqueda aleatoria?**

1. **Mismo presupuesto.** La búsqueda aleatoria recibe exactamente las mismas evaluaciones de fitness que el AG: 1430 por corrida. Comparar por número de generaciones sería injusto.
2. **Varias semillas.** Hay 10 corridas de cada método. No se compara una corrida suelta.
3. **Métricas:**
   - Fitness final: AG 0.9968 de media frente a 0.9810 de la búsqueda aleatoria.
   - Test de Mann-Whitney U unilateral: U = 100, p = 9·10⁻⁵. Este test no asume normalidad.
   - A₁₂ de Vargha-Delaney = 1.0: en todos los pares, la corrida del AG supera a la aleatoria. El AG gana en 10 de 10 semillas.
   - Curva de mejor fitness contra evaluaciones: las dos van parejas durante unas 100 evaluaciones. Después la búsqueda aleatoria se estanca, porque mejorar al azar en 14 dimensiones es cada vez menos probable, y el AG sigue subiendo porque aprovecha la información de la población.
4. **Validación auditiva.** Una encuesta ciega a 5–10 personas puntúa Gen 0, la referencia y el mejor evolucionado. Así se comprueba que la mejora numérica también se oye.

**Sensibilidad (tornado).**
- Hiperparámetros: los que más pesan son el tamaño de población (10 → 0.9925, 60 → 0.9978) y α del cruce blend. El elitismo, entre 0 y 6, casi no cambia el resultado.
- Genes: los que más cambian el fitness son el sostenido, la frecuencia de vibrato y el decaimiento. Los armónicos altos influyen poco, y en esa zona plana de la superficie hay riesgo de deriva genética.

**Limitaciones del AG en este dominio.**
- Cada evaluación es cara: hay que sintetizar audio y calcular una STFT. Por eso el fitness se mide sobre una sola nota.
- El fitness en dB no equivale a la percepción humana; de ahí la encuesta.
- El AG solo puede encontrar timbres que el sintetizador aditivo es capaz de producir.
- Si la detección de pitch falla, el AG no lo corrige, porque evoluciona el timbre y no la melodía.
- La superficie de fitness tiene mesetas: hay genes con muy poca influencia.

**Referencias**
- Eiben, A. E., & Smith, J. E. (2015). *Introduction to Evolutionary Computing* (2.ª ed.). Springer. Cap. 4 (operadores para representación real) y cap. 9 (evaluación experimental).
- Eshelman, L. J., & Schaffer, J. D. (1993). Real-coded genetic algorithms and interval-schemata (BLX-α). *Foundations of Genetic Algorithms 2*.
- Michalewicz, Z. (1996). *Genetic Algorithms + Data Structures = Evolution Programs*. Springer (mutación no uniforme).
- Vargha, A., & Delaney, H. D. (2000). A critique and improvement of the CL common language effect size statistics. *J. Educational and Behavioral Statistics*, 25(2).
