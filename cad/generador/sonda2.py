"""Depurar las relaciones de posición por API."""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swx
from swx import s, Ensamble

SAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sonda"))


def intento(nombre, fn):
    try:
        print(f"[{nombre}] ->", fn())
    except Exception:  # noqa: BLE001
        print(f"[{nombre}] EXCEPCIÓN")
        traceback.print_exc(limit=2)


def main():
    swx.iniciar()
    e = Ensamble("sonda_top2", SAL)
    c1 = e.poner(os.path.join(SAL, "sonda_sub.SLDASM"), fijo=True)
    c2 = e.poner(os.path.join(SAL, "sonda_sub.SLDASM"), None, (0, -300, 0), fijo=False)
    print("componentes:", [s.cast(c, "IComponent2").Name2 for c in e.asm.GetComponents(False)])
    anid = e.componente("sonda_sub-1/sonda_b")
    md, asm = e.md, e.asm

    # nombres de las operaciones de un componente
    f = c2.FirstFeature(); nombres = []
    while f is not None and len(nombres) < 8:
        f = s.cast(f, "IFeature"); nombres.append((f.Name, f.GetTypeName2())); f = f.GetNextFeature()
    print("operaciones c2:", nombres)

    def mate_raw(codigo):
        r = asm.AddMate5(codigo, 2, False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False, False, 0)
        md.ClearSelection2(True)
        return r

    def planos_paralelos():
        md.ClearSelection2(True)
        a = e.plano(c2, "lateral").Select2(False, 1); b = e.plano(c1, "lateral").Select2(True, 1)
        n = s.cast(md.SelectionManager, "ISelectionMgr").GetSelectedObjectCount2(-1)
        return a, b, n, mate_raw(3)

    intento("paralelo plano-plano", planos_paralelos)

    def origen_origen_feat():
        md.ClearSelection2(True)
        a = e.origen(c2).Select2(False, 1); b = e.origen(c1).Select2(True, 1)
        sm = s.cast(md.SelectionManager, "ISelectionMgr")
        n = sm.GetSelectedObjectCount2(-1)
        tipos = [sm.GetSelectedObjectType3(i, -1) for i in range(1, n + 1)]
        return a, b, n, tipos, mate_raw(0)

    intento("coincidente origen-origen (por operación)", origen_origen_feat)

    def origen_por_nombre():
        md.ClearSelection2(True)
        nom_o = e.origen(c2).Name
        t = e.titulo.rsplit(".", 1)[0]
        res = {}
        for pn in ("Point1", "Punto1"):
            n1 = f"{pn}@{nom_o}@{c2.Name2}@{t}"
            ok = md.Extension.SelectByID2(n1, "EXTSKETCHPOINT", 0, 0, 0, False, 1, None, 0)
            res[n1] = ok
            md.ClearSelection2(True)
        return res

    intento("seleccionar origen por nombre", origen_por_nombre)

    def origen_origen_nombre():
        md.ClearSelection2(True)
        t = e.titulo.rsplit(".", 1)[0]
        nom_o = e.origen(c2).Name
        n1 = f"Point1@{nom_o}@{c2.Name2}@{t}"
        nom_a = e.origen(anid).Name
        n2 = f"Point1@{nom_a}@{anid.Name2.replace('/', '@')}@{t}"
        a = md.Extension.SelectByID2(n1, "EXTSKETCHPOINT", 0, 0, 0, False, 1, None, 0)
        b = md.Extension.SelectByID2(n2, "EXTSKETCHPOINT", 0, 0, 0, True, 1, None, 0)
        # variante de nombre anidado
        if not b:
            partes = anid.Name2.split("/")
            n2 = f"Point1@{nom_a}@{partes[0]}@{t}/{partes[1]}@{partes[0].rsplit('-', 1)[0]}"
            b = md.Extension.SelectByID2(n2, "EXTSKETCHPOINT", 0, 0, 0, True, 1, None, 0)
        return n1, a, n2, b, mate_raw(0)

    intento("coincidente origen-origen anidado (por nombre)", origen_origen_nombre)

    def origen_plano():
        md.ClearSelection2(True)
        t = e.titulo.rsplit(".", 1)[0]
        n1 = f"Point1@{e.origen(c2).Name}@{c2.Name2}@{t}"
        a = md.Extension.SelectByID2(n1, "EXTSKETCHPOINT", 0, 0, 0, False, 1, None, 0)
        b = e.plano(anid, "frontal").Select2(True, 1)
        return a, b, mate_raw(0)

    intento("coincidente punto-plano anidado", origen_plano)
    md.EditRebuild3()
    print("transformación c2:", [round(v, 4) for v in c2.Transform2.ArrayData][9:12])
    e.guardar()
    with open(os.path.join(SAL, "sonda_top2.png"), "wb") as f:
        f.write(s.captura("isometrica", 900, 700))


if __name__ == "__main__":
    main()
