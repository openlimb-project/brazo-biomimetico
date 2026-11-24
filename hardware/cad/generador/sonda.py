"""Prueba de las funciones delicadas de la API antes de generar el brazo completo."""
import math
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swx
from swx import s, Pieza, Ensamble

SAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sonda"))
os.makedirs(SAL, exist_ok=True)


def paso(nombre, fn):
    try:
        r = fn()
        print(f"[OK] {nombre}: {r}")
        return r
    except Exception:  # noqa: BLE001
        print(f"[FALLO] {nombre}")
        traceback.print_exc(limit=3)
        return None


def main():
    swx.iniciar()

    def pieza_a():
        p = Pieza("sonda_a", SAL)
        p.rev("y", 9, 0, [(-12, 12.5), (-50, 11.2), (-120, 10.3), (-200, 10.5), (-240, 11.5)], curva=True, nombre="Diafisis")
        p.esfera((0, 0, 0), 22, nombre="Cabeza")
        p.ext("frontal", [{"tipo": "polilinea", "puntos": [(0, -260), (30, -260), (30, -250), (0, -250)]}], 5, 8, nombre="PlacaFrontal")
        p.ext("lateral", [{"tipo": "circulo", "x": 20, "y": -100, "r": 4}], 30, 40, nombre="CilLateral")
        p.ext("superior", [{"tipo": "circulo", "x": -40, "y": 15, "r": 3}], -300, -280, nombre="CilSuperior")
        p.rev("x", -150, 10, [(40, 3), (60, 3)], nombre="RevX")
        p.rev("a", -30, -150, [(20, 2), (35, 2)], nombre="RevA")
        p.taladro("lateral", [{"tipo": "circulo", "x": 0, "y": 0, "r": 3}], nombre="Taladro")
        caja = swx.caja_pieza(p.md)
        info = p.terminar("hueso", "Nailon 101")
        return caja, info["masa_g"]

    paso("pieza A (revolución con spline, esfera, extrusiones en los 3 planos, taladro)", pieza_a)

    def pieza_b():
        p = Pieza("sonda_b", SAL)
        p.rev("y", 0, 0, [(0, 5), (-40, 5), (-40, 2), (-50, 2)], nombre="Cuerpo")
        return p.terminar("uM", None)["masa_g"]

    paso("pieza B", pieza_b)

    sub = [None]

    def subensamble():
        e = Ensamble("sonda_sub", SAL)
        e.poner(os.path.join(SAL, "sonda_a.SLDPRT"))
        R = swx.marco_hacia((1, 0, 0), (0, 1, 0))          # -Y local hacia +X
        c = e.poner(os.path.join(SAL, "sonda_b.SLDPRT"), R, (100, -100, 0))
        caja = [round(v * 1000, 1) for v in c.GetBox(False, False)]
        e.guardar()
        sub[0] = e
        return caja

    paso("subensamble con pieza girada (esperado x 100..150, y -105..-95)", subensamble)

    def superior():
        e = Ensamble("sonda_top", SAL)
        c1 = e.poner(os.path.join(SAL, "sonda_sub.SLDASM"), fijo=True)
        c2 = e.poner(os.path.join(SAL, "sonda_sub.SLDASM"), None, (0, -300, 0), fijo=False)
        anid = e.componente("sonda_sub-1/sonda_b")
        m1 = e.relacion("coincidente", e.origen(c2), e.origen(anid), "R_punto")
        m2 = e.relacion("paralelo", e.plano(c2, "lateral"), e.plano(c1, "lateral"), "R_paralelo")
        e.md.EditRebuild3()
        t = [round(v, 4) for v in c2.Transform2.ArrayData]
        e.guardar()
        with open(os.path.join(SAL, "sonda_top.png"), "wb") as f:
            f.write(s.captura("isometrica", 900, 700))
        return t[9:12]

    paso("ensamble superior con relaciones (esperado traslación 0.1, -0.1, 0)", superior)

    def stl():
        r = swx.exportar_stl(os.path.join(SAL, "sonda_a.SLDPRT"), os.path.join(SAL, "sonda_a.stl"))
        return os.path.getsize(r)

    paso("STL", stl)


if __name__ == "__main__":
    main()
