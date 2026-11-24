# Brazo Biomimético Abierto: cómo trabajar en este repositorio

El proyecto tiene dos secciones que avanzan a la vez y con la misma estructura:

| Sección | Qué abarca | Carpetas |
|---|---|---|
| `hardware/` | Construcción del brazo: diseño CAD, actuadores, materiales, pruebas físicas e investigación de anatomía y mecánica | `cad/`, `solidworks-mcp/`, `investigacion/`, `pruebas/` |
| `software/` | Control del brazo y conexión con el sistema nervioso: simulador, coordinación (capa 2), lectura de la intención (EMG, TMR) y sensación | `simulador/`, `pruebas/`, `investigacion/` |

Cada sección tiene:
- `ESTADO.md`: dónde estamos, decisiones tomadas, pendientes. Se **reescribe** cuando algo cambia, para que siempre diga la verdad de hoy.
- `BITACORA.md`: una entrada por sesión, la más nueva arriba. **Solo se añade**, no se reescribe.

`INTERFAZ.md`, en la raíz, guarda los datos que comparten las dos secciones (masas, fuerzas, rangos articulares, número de unidades y señales). Cada dato vive ahí una sola vez.

## Al empezar una sesión

1. Identifica qué sección o secciones toca la conversación. Pueden ser las dos.
2. Lee el `ESTADO.md` de cada sección que toque y, si hay datos cruzados, `INTERFAZ.md`.

## Al terminar una sesión (o un bloque de trabajo con resultados)

1. Añade una entrada en la `BITACORA.md` de **cada** sección que se tocó, solo con lo que corresponde a esa sección. Una sesión que trabajó en las dos deja dos entradas.
2. Formato de la entrada:
   ```
   ## AAAA-MM-DD · título corto
   - Hecho: …
   - Decidido: …
   - Pendiente: …
   - Ver también: ../otra-seccion/BITACORA.md (si la sesión tocó las dos)
   ```
3. Actualiza el `ESTADO.md` de esa sección si cambió algo.
4. Si cambió un dato compartido, cámbialo en `INTERFAZ.md` y anota en las dos bitácoras que cambió.

## Reglas que no cambian

- `hardware/cad/generador/param.py` es la fuente de verdad del diseño. Tras regenerar el CAD, ejecutar `hardware/cad/generador/mallas.py`, que copia la geometría a `software/simulador/modelo3d/`.
- Unidades: mm, grados, gramos, N.
- `issues-iniciales.md` es un borrador local: no se sube al repositorio.
- No es un dispositivo médico. Nada de pruebas en personas sin supervisión clínica y ética.
- Simulador local: `python -m http.server 8765 --directory software/simulador` (configurado en `.claude/launch.json`).
- El grafo de Graphify está en `graphify-out/` (no se sube al repositorio). Regenerarlo tras cambios grandes con `/graphify . --update`.
