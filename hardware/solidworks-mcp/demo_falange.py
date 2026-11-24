"""Pieza de demostración: falange con pasadores de articulación y canal de tendón.

Ejecutar:  .venv\\Scripts\\python.exe demo_falange.py
Sirve como ejemplo de uso directo de swlib (sin MCP).
"""
import os
import pythoncom

import swlib as s

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "..", "cad")

LARGO = 40      # distancia entre ejes de articulación (mm)
ANCHO = 14      # alto del perfil (mm)
GROSOR = 12     # espesor (mm)
R_PASADOR = 1.6 # pasador de 3 mm con holgura
R_TENDON = 1.0  # canal para hilo/tendón de 2 mm


def main():
    pythoncom.CoInitialize()
    s.nuevo("pieza")
    perfil = s.croquis([{"tipo": "ranura", "x1": 0, "y1": 0, "x2": LARGO, "y2": 0, "ancho": ANCHO}],
                       "frontal")
    s.extruir(perfil, GROSOR, plano_medio=True)
    agujeros = s.croquis([{"tipo": "circulo", "x": 0, "y": 0, "r": R_PASADOR},
                          {"tipo": "circulo", "x": LARGO, "y": 0, "r": R_PASADOR}],
                         en_cara=(LARGO / 2, 0, GROSOR / 2))
    s.extruir(agujeros, corte=True, pasante=True)
    tendon = s.croquis([{"tipo": "circulo", "x": 0, "y": -ANCHO / 2 + 2.5, "r": R_TENDON}], "lateral")
    s.extruir(tendon, LARGO * 3, corte=True, plano_medio=True)
    s.material("ABS")
    os.makedirs(SALIDA, exist_ok=True)
    ruta = s.guardar(os.path.join(SALIDA, "falange_demo.SLDPRT"))
    s.guardar(os.path.join(SALIDA, "falange_demo.stl"))
    with open(os.path.join(SALIDA, "falange_demo.png"), "wb") as f:
        f.write(s.captura("isometrica", 900, 650))
    print(ruta)
    print(s.masa())


if __name__ == "__main__":
    main()
