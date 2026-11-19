# Licencia del diseño de hardware

SPDX-License-Identifier: CERN-OHL-W-2.0

Copyright (c) 2026 Los colaboradores de Brazo Biomimético Abierto

El diseño físico del brazo está bajo la **CERN Open Hardware Licence Version 2 – Weakly Reciprocal (CERN-OHL-W v2)**. Esto incluye los modelos CAD de `cad/` (`.SLDPRT`, `.SLDASM`, `.STL`), los parámetros de `cad/generador/param.py` y los archivos de geometría que el simulador carga desde `simulador-brazo/modelo3d/`.

Texto oficial completo: <https://ohwr.org/cern_ohl_w_v2.txt>

En resumen (el texto oficial es el que vale):
- Puedes usar, estudiar, fabricar, modificar y vender el diseño.
- Si distribuyes una versión modificada del diseño, o productos fabricados con ella, tienes que publicar el código fuente de esas modificaciones bajo la misma licencia.
- Puedes combinarlo con piezas tuyas que no estén bajo esta licencia (la reciprocidad es «débil»), siempre que esas piezas solo se conecten a través de interfaces.
- El diseño se ofrece **sin ninguna garantía**.

El código (simulador, generador y conector MCP de SolidWorks) está bajo la licencia MIT; ver [LICENSE](LICENSE).
