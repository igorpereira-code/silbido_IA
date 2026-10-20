# Rol 4 — El Estratega (dinámica poblacional)

> Cifras de `results/tablas/rol4_configuraciones.csv` (5 semillas por configuración, base: población 30, elitismo 2,
> 50 generaciones, operadores C3 del Rol 3). **Se obtuvieron con el fitness provisional; deben re-ejecutarse con el
> fitness real del Rol 2 (Restart & Run All en `notebooks/rol4_experimentos.ipynb`) y actualizar los números.**

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
- **Población.** Más individuos exploran más el espacio y mantienen la diversidad más tiempo (pob 60: diversidad
  final 0.041; pob 10: 0.002), pero cada generación cuesta más evaluaciones (60 → 2960; 10 → 410).
- **Elitismo.** Garantiza que el máximo nunca baje (el mejor sobrevive). Con elitismo alto hay menos hijos
  nuevos por generación y la población se parece más al mejor. En los datos el efecto fue pequeño
  (elit 0: 0.9976, elit 1: 0.9984, elit 10: 0.9968; la desviación entre semillas es ~0.001).
- **Criterio de parada.** Más generaciones mejoran el fitness con rendimientos decrecientes
  (25 gen: 0.9941; 50: 0.9968; 100: 0.9994). La parada por estancamiento (10 generaciones sin mejora)
  ahorra evaluaciones cuando la curva ya se aplanó.

## 3. ¿Qué hiperparámetro importa más? (leyendo con cuidado el costo)
Con las **mismas generaciones**, la población (rango 0.0057) y las generaciones (0.0053) son los que más mueven
el resultado; elitismo (0.0008) y mutación (0.0002) casi no.
Pero población y generaciones **cambian el costo**, así que esa comparación no es justa. Con el **mismo presupuesto**:
- ~400 evaluaciones: pob 10 → 0.9927, pob 60 → 0.9845 (la población pequeña gana, porque la grande apenas
  alcanza ~6 generaciones).
- ~1430 evaluaciones: pob 10 (178 gen.) → 0.9985, pob 60 (24 gen.) → 0.9950.

**Conclusión:** la población es importante, pero "más grande = mejor" solo vale si se comparan generaciones iguales.
A igual costo, con este fitness, conviene una población pequeña con más generaciones. Esto matiza el tornado del
Rol 5, que no igualaba el presupuesto.

## 4. Convergencia prematura y deriva genética
- **Convergencia prematura** = la diversidad cae a ~0 mientras el fitness aún está lejos del mejor conocido.
  Criterio usado: diversidad final < 0.05 **y** fitness a más de 0.01 del mejor encontrado en todos los experimentos.
  Resultado: **0 de 80 corridas**. La más cercana es pob=10, que colapsa su diversidad (0.002) pero sin perder fitness.
  No se presentó como problema con esta función; se dejó la opción de inmigrantes aleatorios (`inmigrantes`),
  que se activa si la diversidad baja de 0.05, y se mide su costo en evaluaciones.
- **Deriva genética** = genes casi neutrales se fijan en valores al azar. Se mide con la desviación de cada gen
  del mejor individuo entre semillas (`results/tablas/rol4_deriva_genes.csv`). Un uniforme en [0,1] tiene
  desviación ≈ 0.29: genes con valores cercanos a eso (ej. `vib_frec`: 0.365) no están determinados por el fitness; genes con
  desviación ≈ 0.01 (`amp_h1`, `ataque`) sí convergen al mismo valor en todas las corridas.

## 5. Limitaciones (decirlas antes de que pregunten)
- Cifras con fitness provisional y solo 5 semillas; las diferencias de 0.001–0.002 están dentro del ruido
  (desviación entre semillas ≈ 0.001–0.003). Solo población y generaciones muestran efecto claro.
- Se varió un parámetro a la vez; no se midieron interacciones.
- El fitness del Rol 2 real puede cambiar el orden de importancia.
