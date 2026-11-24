# Software: bitácora

Una entrada por sesión, la más nueva arriba. Solo se añade, no se reescribe. El estado actual está en [`ESTADO.md`](ESTADO.md).
Las entradas anteriores al 2026-11-23 se reconstruyeron a partir de las notas del proyecto.

## 2026-11-23 · Reorganización en hardware/ y software/
- Hecho: `simulador-brazo/` pasa a `software/simulador/` y `resultados/` a `software/pruebas/`. `.claude/launch.json` sirve ahora `software/simulador`.
- Decidido: la clave de `localStorage` (`simulador-brazo-v5`) no cambia, para no perder resultados guardados.
- Ver también: ../hardware/BITACORA.md

## 2026-11-22 · Apuntes parte 3
- Decidido: el umbral humano (≈5°, ≈2,6 cm en la mano) está cerca del paso fino de 3 cm. Conviene probar 6 y 9 cm.
- Pendiente: modelar la fuerza resistente de las unidades apagadas.

## 2026-11-20 · Primeras pruebas con una persona
- Hecho: el autor completó el recorrido de 13 pasos (`pruebas/2026-11-20.md`).
- Resultado: «Por turnos» falla (0/4 con ruido); «Guiar con ayuda» y «Elegir objetivo» logran 8/8 con ruido. Sin ver el brazo: sensación fina 8/8, gruesa 2/8, ninguna 0/8.
- Lectura: la capa 2 funciona en simulación; la capa 3 (sensación) decide.

## 2026-11-19 · Simulador v7: gravedad
- Hecho: el reclutamiento incluye la gravedad. El panel muestra N por músculo y «N·m sin equilibrar».
- Hallazgo: con el hombro a 90° al frente quedan ~0,6 N·m sin equilibrar.

## 2026-11-18 · Simulador v6: modelo biomimético
- Hecho: selector «Modelo de brazo», geometría real del CAD, tendones y reclutamiento por velocidad.

## 2026-11-13 · Inicio
- Decidido: arquitectura en tres capas; se empieza por la capa 2 con un simulador en el navegador.
