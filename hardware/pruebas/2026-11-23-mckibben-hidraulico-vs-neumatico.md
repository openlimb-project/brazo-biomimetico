# Prueba: McKibben hidráulico frente a neumático

- Fecha de la ficha: 2026-11-23
- Estado: **planificada, no empezada**
- Forma parte del banco de pruebas McKibben (ver `../ESTADO.md`).
- Seguridad: es una prueba de banco, sin personas. La hidráulica a presión puede romper la vejiga o soltar un racor y proyectar fluido. Usa gafas, una pantalla transparente delante del espécimen y purga la presión antes de tocar nada.

## Pregunta

¿Un músculo McKibben lleno de líquido funciona mejor que el mismo músculo lleno de aire como unidad motora del brazo? ¿Compensa el peso y la complejidad que añade?

## Hipótesis

1. Con la misma presión, la fuerza estática es casi igual en los dos (depende de la geometría, no del fluido).
2. El hidráulico tiene menos histéresis y mantiene la posición mejor bajo carga, porque el líquido no se comprime.
3. El hidráulico pesa más por unidad (fluido dentro y válvula) y responde más despacio por la viscosidad.
4. Sin presión, los dos ceden con poca fuerza resistente. Este dato importa para el problema abierto de `../../INTERFAZ.md`.

## Espécimen

Fabrica dos músculos idénticos en todo excepto en el fluido:

| Parte | Valor provisional |
|---|---|
| Malla trenzada (PET) | Ø 6 mm en reposo, ángulo de trenzado inicial θ₀ ≈ 25° |
| Vejiga | tubo de látex o silicona, Ø interior 4 mm |
| Longitud activa | 100 mm |
| Terminales | racor dentado + abrazadera; el extremo libre cerrado con tapón y gancho |
| Fluido A | aire |
| Fluido B | agua destilada (más adelante, aceite hidráulico ligero si el agua da problemas) |

El tamaño se elige para que la fuerza sea comparable con la fibra del actuador v1 (40 N, 25 % de contracción). La fórmula de Chou–Hannaford da la fuerza teórica:

F = (π·D²·P / 4) · (3·cos²θ − 1) / sin²θ

Con D = 6 mm y θ = 25 °, el factor es ≈ 232 mm². A 300 kPa da ≈ 70 N teóricos. En la práctica se suele medir entre la mitad y dos tercios de eso.

## Montaje

```
  [fuente de presión] → [regulador] → [manómetro / sensor de presión] → [válvula] → músculo
                                                                                        │
                                                         célula de carga ← gancho ──────┘
                                                         + regla o sensor de desplazamiento
```

- Fuente neumática: compresor pequeño con regulador.
- Fuente hidráulica: jeringa grande con husillo, o bomba pequeña con regulador. Antes de cada serie, purga el aire del circuito.
- Célula de carga de 0–200 N (galga + HX711 vale).
- Desplazamiento: potenciómetro lineal o regla con cámara.
- Para la fuerza isométrica, el extremo libre va fijo a la célula. Para la contracción libre, cuelgan pesas.

## Mediciones

Haz cada medición con los dos fluidos y tres repeticiones.

| # | Medición | Cómo | Qué da |
|---|---|---|---|
| M1 | Fuerza isométrica | longitud fija en 100 mm; presión 0 → 100 → 200 → 300 → 400 kPa | curva fuerza–presión |
| M2 | Contracción libre | carga 5 N; mismas presiones | % de contracción frente a la fibra v1 (25 %) |
| M3 | Histéresis | subir y bajar la presión despacio con carga de 10 N | área del ciclo fuerza–longitud |
| M4 | Rigidez bajo carga | presión fija de 300 kPa; añadir 0 → 20 N | mm de alargamiento por N |
| M5 | Respuesta | escalón 0 → 300 kPa con la válvula abierta del todo | tiempo hasta el 90 % de la fuerza (ms) |
| M6 | Fuerza residual apagado | presión 0; estirar 10 mm | N de resistencia de una unidad apagada |
| M7 | Masa | balanza | g del músculo lleno + g de su válvula; aparte, g de la fuente (bomba o compresor) |
| M8 | Fugas y fatiga | 500 ciclos a 300 kPa | pérdida de fuerza (%) y gotas o fugas observadas |

Solo para el hidráulico, y si la vejiga aguanta: repite M1 hasta 1 MPa para ver cuánto margen de fuerza hay.

## Criterios de decisión

El hidráulico pasa a ser candidato para el brazo si cumple:
- M3 y M4 claramente mejores que el neumático (al menos un 30 % menos de histéresis o de alargamiento);
- M6 ≤ el valor del neumático;
- masa por unidad (M7, sin la fuente) ≤ 1,5 veces la de la fibra v1 (9,5 g) por cada 40 N;
- ninguna fuga en M8.

Si pasa, la propuesta es un **híbrido**: hidráulica solo en los músculos grandes del hombro, donde falta par, y el actuador v1 en codo, antebrazo y muñeca. Si no pasa, se queda el actuador v1 en todo el brazo.

## Datos

_(vacío hasta hacer la prueba)_

| Medición | Neumático | Hidráulico | Nota |
|---|---|---|---|
| M1 F a 300 kPa (N) | | | |
| M2 contracción (%) | | | |
| M3 histéresis | | | |
| M4 rigidez (mm/N) | | | |
| M5 respuesta (ms) | | | |
| M6 residual (N) | | | |
| M7 masa unidad (g) | | | |
| M8 pérdida (%) / fugas | | | |

## Lectura

_(pendiente)_
