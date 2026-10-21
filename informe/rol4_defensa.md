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
solución, y ya no puede mejorar. Se detecta con diversidad < 0.05 y fitness a más de 0.01 del mejor conocido. En las
configuraciones normales apareció en 3 de 80 corridas; la provocamos (pob 8, pm 0.01): 5 de 5 corridas, colapso hacia la
generación 9. Se evita con más población y más mutación (0.8835 → 0.9052 y 0.8993). Los inmigrantes recuperan la
diversidad pero mejoran poco el fitness (0.8890).

**¿Qué es la deriva genética?** En poblaciones finitas, genes que no afectan el fitness cambian y se fijan por azar.
Es más fuerte con poblaciones pequeñas. La vemos en los genes con desviación entre semillas alta.

**¿Qué hiperparámetro importa más?** Población y generaciones (efectos 0.0067 y 0.0040 con mismas generaciones). Pero ambos
cuestan evaluaciones: con ~400 evaluaciones gana la población pequeña (0.9022 vs 0.8906) y con ~1430 hay empate
(0.9072 vs 0.9069).

**¿Por qué la diferencia de elitismo es tan chica?** Está dentro del ruido entre semillas (desviación 0.0004–0.004). No afirmamos
que importe.

**¿Los resultados son definitivos?** Usan el fitness real del Rol 2, pero con solo 5 semillas: las diferencias pequeñas están dentro del ruido.

**¿Usaron algo de deep learning?** No. Solo numpy, un AG real-codificado y operadores clásicos.

**¿Cómo se reproduce?** `Restart & Run All` en `notebooks/rol4_experimentos.ipynb`; semillas 0–4 fijas.

**¿Qué hiciste tú y qué no?** Ciclo, parámetros de población, parada, métricas y experimentos. Los operadores son del Rol 3
y el análisis frente a la búsqueda aleatoria, del Rol 5.
