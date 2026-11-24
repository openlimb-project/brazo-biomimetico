# Interfaz entre hardware y software

Datos que comparten las dos secciones. Cada dato vive **solo aquí**. Si lo cambias, anótalo en la `BITACORA.md` de las dos secciones.

Última revisión: 2026-11-23

## Cómo viaja la geometría

```
hardware/cad/generador/param.py      (fuente de verdad)
        │  generar.py  (SolidWorks, ~1 h)
        ▼
hardware/cad/brazo_v0/  (.SLDPRT, .SLDASM, stl/, modelo.json, masa_total.json)
        │  mallas.py
        ▼
software/simulador/modelo3d/  (modelo.json, mallas.json)  →  simulador y visor 3D
        │
        └─→ hardware/cad/optimizador/inserciones.py  (lee modelo.json y usa el mismo cálculo
            de gravedad que el simulador, bioGravity, para optimizar anclajes del hombro)
```

Si cambia el CAD: regenerar → `mallas.py` → comprobar el simulador → republicar el artefacto con los archivos nuevos.

## Datos compartidos

| Dato | Valor | Origen | Estado |
|---|---|---|---|
| Grados de libertad | 7 (hombro 3, codo 1, antebrazo 1, muñeca 2) | `param.py` | firme |
| Músculos | 15, en pares opuestos | `param.py` | firme |
| Unidades motoras | 52 (3 o 4 por músculo, reclutadas de pequeña a grande) | `param.py` | firme |
| Señales de control | 5 o 6, repartidas por la «médula artificial» | hipótesis de arquitectura | hipótesis |
| Codo | 0–130° | `param.py` / simulador | firme |
| Pronación-supinación | 0–140° | `param.py` / simulador | firme |
| Masa del modelo | 1 585 g (`masa_total.json`) | SolidWorks | **por aclarar**: los apuntes parte 3 dan 1 326 g sin mano (huesos y montura ≈630 g, músculos ≈700 g). Falta confirmar si la diferencia es la mano de referencia |
| Mano supuesta en el simulador | 500 g | simulador | provisional |
| Fuerza máxima por pack | P4 = 160 N, P3 = 120 N | simulador / `actuador_v1/dimensionado.json` | provisional |
| Fibra del actuador v1 | 40 N, contracción 25 %, 9,5 g | `actuador_v1/dimensionado.json` | provisional |
| Paso de sensación en el simulador | fino 3 cm, grueso 12 cm | simulador | falta probar 6 y 9 cm (umbral humano ≈2,6 cm en la mano) |

## Problemas abiertos que cruzan las dos secciones

- Con el hombro recto al frente a 90°, el modelo v0 no se equilibra del todo (~0,6 N·m sin equilibrar). Falta un pectoral real (hardware) y el deltoides medio M03 no participa (software).
- Las unidades motoras apagadas generan fuerza resistente en un actuador real. El simulador todavía no lo modela.
