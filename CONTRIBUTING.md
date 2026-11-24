# Cómo colaborar

Gracias por querer ayudar. Se aceptan issues y pull requests en español o en inglés.

## Primeros pasos

1. Haz un *fork* del repositorio y crea una rama con un nombre descriptivo, por ejemplo `simulador-gravedad`.
2. Haz cambios pequeños y enfocados: un PR por idea.
3. Explica en el PR **qué** cambia y **cómo lo probaste**. Para el simulador sirve una captura; para el CAD, las vistas que genera `sw_ver` o `generar.py`.

## Reglas del proyecto

- **`hardware/cad/generador/param.py` es la fuente de verdad del diseño.** No edites a mano las piezas de `hardware/cad/brazo_v0/`: cambia los parámetros y regenera.
- Si cambias la geometría, vuelve a ejecutar `mallas.py` para que el simulador cargue el modelo nuevo y adjunta los archivos regenerados.
- Unidades: milímetros, grados y gramos.
- El repositorio tiene dos secciones, `hardware/` y `software/`. Si tu cambio afecta a un dato que usa la otra sección (masa, par, rango articular, señal), actualízalo en `INTERFAZ.md`.
- Cualquier afirmación sobre fisiología o neurociencia debe ir acompañada de su fuente (un artículo o un libro).

## Ideas para empezar

- Añadir gravedad y carga externa al simulador.
- Pruebas automáticas para `param.py` (rangos articulares, longitudes de los tendones).
- Portar el generador a FreeCAD o CadQuery para que no haga falta SolidWorks.
- Traducir la interfaz del simulador al inglés.

## Seguridad

Esto es investigación, no un dispositivo médico. No propongas ni documentes pruebas en personas sin supervisión clínica y ética.

## Licencias

Al contribuir aceptas que tu código se publique bajo MIT y tus cambios al diseño de hardware bajo CERN-OHL-W v2.
