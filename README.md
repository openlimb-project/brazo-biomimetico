# Brazo Biomimético Abierto

Prótesis de brazo completo, del hombro a la muñeca, diseñada imitando al brazo humano. En lugar de unos pocos motores rígidos usa **15 músculos elásticos en pares opuestos**. Cada músculo está dividido en **«unidades motoras»** que se reclutan de pequeñas a grandes, como en el cuerpo. El objetivo a largo plazo es un movimiento rápido y natural, y reducir la barrera de control y sensación entre la persona y la prótesis.

> ⚠️ **Proyecto de investigación en fase temprana. No es un dispositivo médico.** No está probado en personas ni certificado. No lo uses en nadie.

*English summary below.*

## Qué hay aquí

El proyecto está dividido en dos secciones que avanzan a la vez. Cada una tiene su `ESTADO.md` (dónde estamos, decisiones, pendientes) y su `BITACORA.md` (qué se hizo en cada sesión). Lo que une a las dos (masas, pares, articulaciones, señales) está en [`INTERFAZ.md`](INTERFAZ.md).

**[`hardware/`](hardware/)**: construcción del brazo, diseño, pruebas físicas e investigación.

| Carpeta | Contenido | Licencia |
|---|---|---|
| [`hardware/cad/generador/`](hardware/cad/generador/) | Generador paramétrico: `param.py` es la fuente de verdad y `generar.py` construye el brazo en SolidWorks | MIT (código) / CERN-OHL-W (parámetros) |
| [`hardware/cad/brazo_v0/`](hardware/cad/brazo_v0/) | Modelo generado: 31 piezas, 15 músculos, 52 unidades motoras, 7 grados de libertad. Incluye STL | CERN-OHL-W |
| [`hardware/cad/actuador_v1/`](hardware/cad/actuador_v1/) | Dimensionado de los packs de unidades motoras | CERN-OHL-W |
| [`hardware/solidworks-mcp/`](hardware/solidworks-mcp/) | Servidor MCP que deja a Claude (u otro cliente MCP) controlar **SolidWorks 2020** por COM: 22 herramientas de croquis, extrusión, ensambles, materiales, capturas… | MIT |

**[`software/`](software/)**: control del brazo y conexión con el sistema nervioso.

| Carpeta | Contenido | Licencia |
|---|---|---|
| [`software/simulador/`](software/simulador/) | Simulador musculoesquelético en el navegador (HTML + JS, sin instalación) y visor 3D del modelo | MIT |
| [`software/pruebas/`](software/pruebas/) | Resultados de las pruebas con el simulador | MIT |

## Cómo probarlo

**Simulador (no necesita nada más que Python o un navegador):**

```bash
python -m http.server 8765 --directory software/simulador
```

Después abre <http://localhost:8765>.

**Regenerar el CAD (Windows + SolidWorks 2020 o más nuevo):**

```bash
py -3.14 -m venv hardware\solidworks-mcp\.venv
hardware\solidworks-mcp\.venv\Scripts\python.exe -m pip install "mcp[cli]" pywin32 pillow
hardware\solidworks-mcp\.venv\Scripts\python.exe hardware\cad\generador\generar.py
```

La generación completa tarda alrededor de una hora. Si se interrumpe, retómala con `--faltan` o con `--desde <etapa>`. Después ejecuta `hardware\cad\generador\mallas.py` para actualizar el visor del simulador.

**Usar el conector de SolidWorks con Claude Code:** copia `.mcp.example.json` a `.mcp.json` y abre Claude Code en esta carpeta. Los detalles están en [`hardware/solidworks-mcp/README.md`](hardware/solidworks-mcp/README.md).

## Arquitectura (hipótesis de trabajo)

1. **Leer la intención** de la persona (EMG o, más adelante, reinervación muscular dirigida).
2. **Coordinar las articulaciones automáticamente**, con una «médula artificial» que reparte 5 o 6 señales entre unas 50 unidades motoras.
3. **Devolver sensación.**

Estamos trabajando en la capa 2, primero en simulación. El músculo físico previsto es un motor con un tendón y un resorte en serie. El banco de pruebas del reclutamiento usará músculos neumáticos tipo McKibben. El codo es la primera articulación que se construirá.

## Hoja de ruta

- [x] Diseño paramétrico v0 del brazo completo
- [x] Simulador con geometría real y reclutamiento por unidades motoras
- [ ] Gravedad y cargas en el simulador
- [ ] Control desde señales simuladas de EMG
- [ ] Prototipo físico del codo biomimético
- [ ] Banco de pruebas con músculos McKibben

## Cómo colaborar

Buscamos ayuda de gente de biomecánica, control, neurociencia, CAD, impresión 3D y desarrollo web. Para empezar, lee [CONTRIBUTING.md](CONTRIBUTING.md) y busca issues con la etiqueta `buen-primer-issue`.

## Licencia

El código está bajo [MIT](LICENSE) y el diseño de hardware bajo [CERN-OHL-W v2](LICENSE-HARDWARE.md).

---

## English summary

**Open Biomimetic Arm**: an open-source full-arm prosthesis (shoulder to wrist) that mimics human anatomy. It has 15 antagonistic elastic muscles split into 52 "motor units" that are recruited from small to large, plus an "artificial spinal cord" layer that maps a few control signals onto many actuators. The repo contains a browser-based musculoskeletal simulator, a parametric CAD generator for SolidWorks, the generated 7-DOF model (STL included), and an MCP server that lets Claude or any other MCP client drive **SolidWorks 2020** over COM. Early research only, **not a medical device**. Code is MIT and hardware is CERN-OHL-W v2. Contributions and issues in English are welcome.
