# Hardware: bitácora

Una entrada por sesión, la más nueva arriba. Solo se añade, no se reescribe. El estado actual está en [`ESTADO.md`](ESTADO.md).
Las entradas anteriores al 2026-11-23 se reconstruyeron a partir de las notas del proyecto.

## 2026-11-23 · Reorganización en hardware/ y software/
- Hecho: `cad/` y `solidworks-mcp/` pasan a `hardware/`. Se ajustaron las rutas de `mallas.py` y `inserciones.py` (escriben y leen en `software/simulador/modelo3d/`) y de `.mcp.json`. Nuevo entorno Python del conector en `hardware/solidworks-mcp/.venv`.
- Decidido: los datos compartidos con el software viven en `../INTERFAZ.md`.
- Pendiente: aclarar la masa del modelo (1 585 g frente a 1 326 g sin mano).
- Ver también: ../software/BITACORA.md

## 2026-11-22 · Apuntes parte 3: hueso impreso (Lithoz)
- Hecho: revisión del brazo de Mánchester y de los haces de músculos de fluido con reclutamiento variable.
- Decidido: el reparto de masa de v0 es ≈630 g de huesos y montura y ≈700 g de músculos.
- Pendiente: seis experimentos propuestos, ninguno empezado.

## 2026-11-20 · Actuador v1 y optimizador del hombro
- Hecho: `cad/actuador_v1/` (packs P3 y P4) y `cad/optimizador/inserciones.py`, que optimiza los anclajes del hombro con el mismo cálculo de gravedad que el simulador.

## 2026-11-19 · Publicación
- Hecho: repositorio público, con código bajo MIT y hardware bajo CERN-OHL-W v2.

## 2026-11-18 · Modelo 3D v0
- Hecho: generador paramétrico (`param.py` → `generar.py` → `mallas.py`). Brazo v0: 31 piezas, 15 músculos, 52 unidades motoras, 7 GDL.

## 2026-11-16 · Enfoque biomimético
- Decidido: 15 músculos en pares opuestos con unidades motoras; músculo = motor + tendón + resorte; banco McKibben; el codo va primero.

## 2026-11-13 · Inicio
- Decidido: desarticulación de hombro, 7 GDL, mano comercial.
