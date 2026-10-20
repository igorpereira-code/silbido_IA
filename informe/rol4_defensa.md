# Rol 4 — Guía de defensa (preguntas probables)

**¿Qué es el ciclo generacional con elitismo?** Cada generación se crea casi toda la población nueva (hijos),
salvo los `elitismo` mejores, que pasan sin cambios. Así el mejor fitness nunca baja.

**¿Por qué solo se evalúan los hijos?** Los elites ya tienen su fitness calculado y no cambiaron; re-evaluarlos
gasta evaluaciones sin información nueva. Evaluaciones = N + T·(N − elitismo).

**¿Por qué guardas el "mejor histórico"?** Con elitismo 0 el mejor podría perderse en una generación; así
el resultado nunca es peor que lo ya visto.

**¿Qué criterio de parada usan y por qué?** Máximo de generaciones (presupuesto fijo, reproducible y comparable con
la búsqueda aleatoria del Rol 5). Opcional: estancamiento (paciencia 10 generaciones sin mejorar > 1e-4).

**¿Qué es convergencia prematura?** La población se vuelve casi idéntica (diversidad ≈ 0) antes de llegar a una buena
solución, y ya no puede mejorar. Se detecta con diversidad < 0.05 y fitness lejos del mejor conocido. En nuestros
datos no ocurrió en ninguna de las 80 corridas. Se previene con población mayor, mutación y/o inmigrantes.

**¿Qué es la deriva genética?** En poblaciones finitas, genes que no afectan el fitness cambian y se fijan por azar.
Es más fuerte con poblaciones pequeñas. La vemos en los genes con desviación entre semillas alta.

**¿Qué hiperparámetro importa más?** Población y generaciones. Pero ambos cuestan evaluaciones; a igual
presupuesto la población pequeña ganó (pob 10: 0.9985 vs pob 60: 0.9950 con ~1430 evaluaciones).

**¿Por qué la diferencia de elitismo es tan chica?** Está dentro del ruido entre semillas (~0.001). No afirmamos
que importe.

**¿Los resultados son definitivos?** No: se hicieron con el fitness provisional; se repiten con el real del Rol 2.

**¿Usaron algo de deep learning?** No. Solo numpy, un AG real-codificado y operadores clásicos.

**¿Cómo se reproduce?** `Restart & Run All` en `notebooks/rol4_experimentos.ipynb`; semillas 0–4 fijas.

**¿Qué hiciste tú y qué no?** Ciclo, parámetros de población, parada, métricas y experimentos. Los operadores son del Rol 3
y el análisis frente a la búsqueda aleatoria, del Rol 5.
