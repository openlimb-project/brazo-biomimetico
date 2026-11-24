# Conector Claude ↔ SolidWorks 2020

Servidor MCP propio que deja a Claude controlar el SolidWorks 2020 Premium (API 28) de esta PC
por COM. Lo hicimos a medida porque los conectores públicos piden SolidWorks 2022 o más nuevo.

## Cómo se usa

1. Abre una sesión de Claude Code en `Experimento_#001` (ahí está `.mcp.json` con la entrada
   `solidworks`). Si la sesión ya estaba abierta, reiníciala para que cargue el servidor.
   Los archivos de SolidWorks del brazo van en `../cad/`; el simulador web está en `../../software/simulador/`.
2. SolidWorks no necesita estar abierto: el conector lo arranca solo. Si ya está abierto, se engancha
   a esa ventana. No lo minimices mientras Claude toma capturas.
3. Pídele a Claude cosas como "haz una falange de 40 mm entre ejes con pasador de 3 mm y
   canal para el tendón", "ponle Nailon 101 y dime cuánto pesa" o "exporta el STL".

## Herramientas (22)

| Herramienta | Qué hace |
|---|---|
| `sw_estado` | Versión, documentos abiertos, árbol de operaciones |
| `sw_nuevo`, `sw_abrir`, `sw_activar`, `sw_guardar` | Documentos; guardar a `.stl/.step/.igs/.x_t/.3mf` exporta |
| `sw_croquis` | Círculo, rectángulo, línea, eje, polilínea, arco, ranura, polígono, spline, elipse |
| `sw_extruir`, `sw_revolucion` | Saliente o corte (ciego, pasante, plano medio, dos sentidos) |
| `sw_redondeo`, `sw_chaflan`, `sw_vaciado` | Aristas/caras elegidas por un punto `[x,y,z]` en mm |
| `sw_plano`, `sw_eje`, `sw_patron_circular` | Geometría de referencia y patrones |
| `sw_cota` | Leer/cambiar cotas (`D1@Sketch1`) → diseño paramétrico |
| `sw_editar` | Deshacer, borrar, suprimir/activar operaciones |
| `sw_materiales`, `sw_material`, `sw_masa` | Biblioteca de materiales, asignación, masa/volumen/CdM |
| `sw_ver` | Captura PNG de la vista (isométrica, frontal…), para que Claude revise |
| `sw_insertar_componente` | Ensambles |
| `sw_python` | Python con la API COM completa, para todo lo demás (relaciones de posición, ecuaciones…) |

Unidades: milímetros y grados. Planos: `frontal` (XY), `superior` (XZ), `lateral` (YZ).

## Archivos

- `swlib.py`: la librería (se puede usar sin MCP: `import swlib as s`).
- `server.py`: el servidor MCP (paquete `mcp` 2.x, `MCPServer`).
- `demo_falange.py`: ejemplo completo; genera `../cad/falange_demo.*`.
- `.venv/`: Python 3.14 con `mcp`, `pywin32`, `pillow`.

## Detalles técnicos (por si algo falla)

- SolidWorks no publica *typeinfo*: se usa enlace temprano con `sldworks.tlb` (gen_py) y
  `QueryInterface` automático. Los métodos que devuelven objetos sin tipo se tipan por la
  tabla `RETORNOS` de `swlib.py`. Si en `sw_python` algo devuelve un objeto "mudo", usa
  `cast(obj, 'IFeature')` o `tipar(obj)`.
- La API exige nombres de material en inglés aunque la interfaz esté en español; `swlib`
  traduce por `matid` (`Nailon 101` → `Nylon 101`).
- Todas las llamadas COM van por un único hilo.
- Reinstalar dependencias:
  `py -3.14 -m venv .venv` y luego `.venv\Scripts\python.exe -m pip install "mcp[cli]" pywin32 pillow`.
