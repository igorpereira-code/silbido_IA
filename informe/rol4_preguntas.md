# Rol 4 — El Estratega (dinámica poblacional)

> Cifras de `results/tablas/rol4_configuraciones.csv` con el **fitness real del Rol 2** (5 semillas por configuración;
> base: población 30, elitismo 2, 50 generaciones, operadores C3 del Rol 3). Para reproducir:
> `Restart & Run All` en `notebooks/rol4_experimentos.ipynb` (~15 min).

## 1. Qué hace mi módulo (`src/rol4_ag.py`)
`ejecutar_ag(config, fitness_fn, seed)` ejecuta el ciclo generacional con elitismo:
1. Genera la población inicial aleatoria en [0,1]^14 y la evalúa (Gen 0).
2. En cada generación: ordena por fitness; los `elitismo` mejores pasan intactos; los demás se crean con
   `rol3_operadores.reproducir` (selección → cruce → mutación → reparar); se evalúan solo los hijos.
3. Registra máximo, media, desviación, diversidad y evaluaciones acumuladas.
4. Termina al llegar a `generaciones` (o, si se activa, tras `paciencia` generaciones sin mejora mayor a la tolerancia).
5. Devuelve el mejor individuo histórico, el mejor de Gen 0 y el historial.

Evaluaciones totales = N + T·(N − elitismo). Con la base: 30 + 50·28 = **1430**.
No reimplementa operadores; el Rol 5 usa ese número como presupuesto de la búsqueda aleatoria.

## 2. Pregunta teórica: ¿cómo influyen población, elitismo y criterio de parada?
- **Población.** Más individuos mantienen la diversidad más tiempo (pob 60: diversidad final 0.023; pob 10: 0.003) y
  llegan a mejor fitness con las mismas generaciones (0.9089 vs 0.9022), pero cada generación cuesta más
  evaluaciones (60 → 2960; 10 → 410).
- **Elitismo.** Garantiza que el máximo nunca baje (el mejor sobrevive). Con elitismo alto hay menos hijos
  nuevos por generación. En los datos el efecto fue pequeño (elit 0: 0.9087; elit 1: 0.9063; elit 10: 0.9077), del
  orden del ruido entre semillas (desviación 0.0004–0.0040), así que no afirmamos que importe.
- **Criterio de parada.** Más generaciones mejoran el fitness con rendimientos decrecientes
  (25 gen: 0.9033; 50: 0.9051; 100: 0.9073). La parada por estancamiento (10 generaciones sin mejora) terminó
  en ~60 generaciones con 0.9088, usando 1716 evaluaciones en lugar de las 2830 de 100 generaciones.

## 3. ¿Qué hiperparámetro importa más? (leyendo con cuidado el costo)
Con las **mismas generaciones**, el efecto (fitness con valor alto − valor bajo) es: población 0.0067,
generaciones 0.0040, elitismo 0.0010, mutación 0.0004. Población y generaciones son los que más mueven el resultado.
Pero ambos **cambian el costo**, así que esa comparación no es justa. Con el **mismo presupuesto**:
- ~400 evaluaciones: pob 10 → 0.9022, pob 60 → 0.8906. Con poco presupuesto gana la población pequeña, porque la
  grande apenas alcanza ~6 generaciones.
- ~1430 evaluaciones: pob 10 (178 gen.) → 0.9072, pob 60 (24 gen.) → 0.9069. **Empate** (diferencia 0.0003, dentro del ruido).

**Conclusión:** "población grande = mejor" solo se cumple al comparar con las mismas generaciones. Al igualar el costo
el resultado depende del presupuesto: con poco gana la población pequeña y con ~1430 evaluaciones no hay diferencia. Esto
matiza el tornado del Rol 5, que no igualaba el presupuesto.

## 4. Pregunta teórica: ¿qué es la convergencia prematura? ¿Cómo se detecta y cómo se evita?
**Qué es.** La población se vuelve casi idéntica (diversidad ≈ 0) antes de llegar a una buena solución, y el AG ya no
puede mejorar: los cruces entre individuos iguales no crean nada nuevo y la mutación es muy pequeña para escapar.

**Cómo se detecta.** Con dos señales a la vez: diversidad < 0.05 (diversidad = desviación media por gen, normalizada)
**y** fitness final a más de 0.01 del mejor encontrado en todos los experimentos (0.9103). Que la diversidad baje
sola no basta: al final de una corrida buena también baja (convergencia sana).

**Evidencia concreta.**
- En las 16 configuraciones normales hubo **3 corridas prematuras de 80** (base, pob=10 y pob=20, una cada una, con
  fitness 0.896–0.900), es decir, incluso con parámetros razonables aparece de vez en cuando.
- Para estudiarla se **provocó** (población 8, mutación 0.01) y se probaron remedios:

| Configuración | fitness final | diversidad final | gen. de colapso | corridas prematuras |
|---|---|---|---|---|
| base (30, pm defecto) | 0.9051 | 0.015 | 40 | 1 de 5 |
| prem: pob=8, pm=0.01 | 0.8835 | 0.0002 | 9 | **5 de 5** |
| prem + inmigrantes | 0.8890 | 0.569 | — | 0 de 5 |
| prem + pm=0.15 | 0.8993 | 0.0015 | 37 | 2 de 5 |
| prem + pob=30 | 0.9052 | 0.0045 | 26 | 0 de 5 |

La población provocada colapsa hacia la generación 9 y queda 0.022 por debajo de la base
(gráfico `rol4_prematura_remedios.png`).

**Cómo se evita (según los datos).** Más población y más mutación recuperan el fitness (0.8835 → 0.9052 y 0.8993). Los
inmigrantes aleatorios **restauran la diversidad** (0.0002 → 0.57) pero mejoran poco el fitness (0.8835 → 0.8890): un
individuo aleatorio casi nunca supera a los élites y solo cuesta evaluaciones (~+63). Es decir, diversidad alta no
equivale a mejor resultado.

**Deriva genética** = genes casi neutrales se fijan en valores al azar. Se mide con la desviación de cada gen del
mejor individuo entre semillas (`results/tablas/rol4_deriva_genes.csv`). Un uniforme en [0,1] tiene desviación ≈ 0.29:
genes cercanos o mayores (`liberacion` 0.48, `vib_frec` 0.39, `decaimiento` 0.28, `vib_prof` 0.28) no quedan
determinados por el fitness; genes con desviación ≈ 0.01–0.02 (`ataque` 0.002, `amp_h7` 0.011, `sostenido` 0.021)
convergen al mismo valor en todas las corridas.

## 5. Limitaciones (decirlas antes de que pregunten)
- Solo 5 semillas por configuración: diferencias menores a ~0.004 están dentro del ruido (desviación entre semillas
  0.0004–0.0053). Solo población y generaciones muestran efecto claro.
- Se varió un parámetro a la vez; no se midieron interacciones.
- El fitness real tiene un rango estrecho (~0.88–0.91), así que las diferencias absolutas son pequeñas.

## 6. Resumen de lo entregado frente a lo pedido
- AG completo y funcional: `src/rol4_ag.py` (14 tests).
- Tabla experimental: **20 configuraciones** (16 variando un parámetro + 4 del caso provocado), 5 semillas cada una.
- Curvas de convergencia **por configuración**: `results/graficos/rol4_convergencia_todas.png` y gráficos agrupados.
- Análisis "¿qué hiperparámetro importa más?": sección 3.
- Estancamiento prematuro y deriva genética: sección 4.

## Referencias
- Goldberg, D. E. (1989). *Genetic Algorithms in Search, Optimization and Machine Learning*. Addison-Wesley.
- Eiben, A. E. & Smith, J. E. (2015). *Introduction to Evolutionary Computing* (2.ª ed.). Springer.
- Michalewicz, Z. (1996). *Genetic Algorithms + Data Structures = Evolution Programs* (3.ª ed.). Springer.
- De Jong, K. A. (1975). *An Analysis of the Behavior of a Class of Genetic Adaptive Systems*. Tesis doctoral, Univ. de Michigan.
