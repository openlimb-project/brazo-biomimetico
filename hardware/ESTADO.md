# Hardware: estado

Construcción del brazo: diseño, actuadores, materiales, pruebas físicas e investigación.
Datos compartidos con el software: [`../INTERFAZ.md`](../INTERFAZ.md) · Historial: [`BITACORA.md`](BITACORA.md)

Última revisión: 2026-11-23

## Dónde estamos

- **Modelo v0 completo** en `cad/brazo_v0/` (`Brazo_biomimetico_v0.SLDASM` y `_pose`), generado por código desde `cad/generador/`. 31 piezas, 15 músculos, 52 unidades motoras, 7 GDL.
- **Actuador v1** en `cad/actuador_v1/`: packs P3 y P4 de fibras motor + tendón + resorte en serie (`Pack_v1_P3/P4.SLDASM`, `dimensionado.json`).
- **Optimizador de anclajes del hombro** en `cad/optimizador/` (`inserciones.py`, resultados en `resultados/`).
- **Conector SolidWorks** en `solidworks-mcp/`: 22 herramientas `sw_*` para SolidWorks 2020 por COM.
- No hay nada construido físicamente todavía.

## Decisiones tomadas

- Desarticulación de hombro, 7 GDL, mano comercial acoplada (2026-11-13).
- Enfoque biomimético: 15 músculos elásticos en pares opuestos, divididos en unidades motoras (2026-11-16).
- Músculo físico: motor + tendón + resorte en serie (2026-11-16).
- Banco de pruebas del reclutamiento: haces de músculos neumáticos tipo McKibben (2026-11-16).
- El codo biomimético es la primera articulación que se construirá (2026-11-16).
- `cad/generador/param.py` es la fuente de verdad: no se editan las piezas a mano.

## Pendientes

- [ ] Prototipo físico del codo.
- [ ] Banco de pruebas McKibben.
- [ ] Añadir un pectoral real al modelo (ver el problema del hombro en `INTERFAZ.md`).
- [ ] Aclarar la masa del modelo (1 585 g frente a 1 326 g sin mano).
- [ ] Seis experimentos propuestos en los apuntes parte 3, ninguno empezado.
- [ ] Tests de `param.py` y generador con herramientas libres (CadQuery o FreeCAD), ver `issues-iniciales.md`.

## Investigación

Los apuntes largos están como documentos en Descartes/Cowork. Aquí solo se guardan notas y fuentes que afectan al diseño (`investigacion/`).
- Proyecto más parecido: brazo biomimético de Mánchester (motor + tendón + resorte; huesos, ligamentos y cartílago).
- Referencia de actuador: «haces de músculos de fluido con reclutamiento variable».
- Hueso impreso en cerámica (Lithoz) como posible material.

## Cómo se trabaja aquí

- Regenerar: `solidworks-mcp\.venv\Scripts\python.exe cad\generador\generar.py` (~1 h; si se atasca, `--faltan` o `--desde <etapa>`). Después, `cad\generador\mallas.py`.
- Pruebas físicas: un archivo por prueba en `pruebas/`, con fecha, montaje, datos y lectura.
