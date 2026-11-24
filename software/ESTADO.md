# Software: estado

Control del brazo y conexión con el sistema nervioso.
Datos compartidos con el hardware: [`../INTERFAZ.md`](../INTERFAZ.md) · Historial: [`BITACORA.md`](BITACORA.md)

Última revisión: 2026-11-23

## Arquitectura (hipótesis de trabajo)

1. **Leer la intención** (EMG; más adelante, reinervación muscular dirigida, TMR).
2. **Coordinar las articulaciones automáticamente**: una «médula artificial» reparte 5 o 6 señales entre unas 50 unidades motoras.
3. **Devolver sensación.**

## Dónde estamos

- **Simulador** en `simulador/index.html`, con un recorrido guiado de 17 pasos (eran 13 en la prueba del 2026-11-20), modos «Por turnos», «Guiar la mano», «Guiar con ayuda» y «Elegir objetivo», y un modelo de brazo biomimético (por defecto) o simple.
  - Con el modelo biomimético usa la geometría real del CAD (`simulador/modelo3d/modelo.json` y `mallas.json`), muestra los tendones y recluta unidades motoras por velocidad de acortamiento **y por gravedad** (peso por grupo + mano de 500 g; reparto por mínimos cuadrados con fuerzas ≥ 0).
  - Gancho de prueba: `__sim.bioLoad(grados)`.
- **Visor 3D** en `simulador/modelo3d/index.html`.
- **Primeras pruebas con una persona** (el autor, 2026-11-20): `pruebas/2026-11-20.md`. La capa 2 funciona en simulación. La sensación (capa 3) es la que decide si se puede controlar el brazo sin verlo.

## Decisiones tomadas

- Se empezó por la capa 2 porque sirve con cirugía o sin ella (2026-11-13).
- El simulador debe explicarse solo: controles visibles, guiado, respetando el cuerpo del sujeto.
- Los resultados se guardan en `localStorage` con la clave `simulador-brazo-v5`; los del modelo biomimético llevan el sufijo `|bio`.

## Pendientes

- [ ] Decidir la ruta: con cirugía (TMR) o sin ella, y quién sería el primer usuario.
- [ ] Control desde señales simuladas de EMG (capa 1).
- [ ] Probar pasos de sensación intermedios (6 y 9 cm).
- [ ] Modelar la fuerza resistente de las unidades apagadas.
- [ ] Revisar por qué el deltoides medio M03 no participa con el hombro a 90°.
- [ ] Selector de idioma ES/EN (issue 1 de `issues-iniciales.md`).

## Cómo se trabaja aquí

- Servidor local: `python -m http.server 8765 --directory software/simulador` → <http://localhost:8765>.
- Si el CAD cambia, la geometría llega aquí con `hardware/cad/generador/mallas.py`. No editar `modelo3d/*.json` a mano.
- Pruebas: un archivo por sesión de pruebas en `pruebas/AAAA-MM-DD.md`, con quién la hizo, las tablas y la lectura.
- Investigación de neurociencia, EMG y sensación: `investigacion/`, siempre con su fuente.
