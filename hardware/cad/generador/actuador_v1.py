"""Actuador v1 — «fibra torsional» (twisted string actuator) para el brazo biomimético.

Idea: en lugar de un motor con reductora y husillo por unidad motora (v0: cilindros de Ø10–16 x 50–70 mm),
cada unidad es un micromotor de Ø11 x 36 mm que RETUERCE dos cuerdas de UHMWPE. Al retorcerse, las cuerdas
se acortan y tiran del tendón. La propia cuerda es la reductora (relación variable, muy alta al principio),
así que no hace falta husillo, y lo que recorre el brazo es una «fibra» de Ø3 mm, como un músculo real.

Uso (desde la carpeta del proyecto):
    py -3.13 cad\\generador\\actuador_v1.py                 -> solo dimensionado (no necesita SolidWorks)
    solidworks-mcp\\.venv\\Scripts\\python.exe cad\\generador\\actuador_v1.py --cad
                                                            -> además genera piezas, packs, STL y capturas
Salida: cad/actuador_v1/
"""
import argparse
import json
import math
import os
import random
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import param as P  # noqa: E402

SAL = os.path.abspath(os.path.join(AQUI, "..", "actuador_v1"))

# ====================================================================== parámetros (mm, N, s)
FIBRA = {
    "r_motor": 5.5,          # carcasa Ø11: micromotor coreless Ø10 + reductora planetaria 4:1 + encoder magnético
    "largo_motor": 32.0,     # encoder 4 + motor 17 + reductora 9 + rodamiento 2
    "largo_cubo": 4.0,       # cubo de salida donde se atan las cuerdas
    "r_cuerda": 0.45,        # radio efectivo del par de cuerdas (2 x UHMWPE Ø0,6 mm)
    "r_haz": 0.75,           # radio del haz retorcido al máximo (para dibujarlo)
    "funda": (1.25, 1.65),   # funda de PTFE: radio interior, exterior
    "contraccion": 0.25,     # contracción de trabajo (25 % del largo de cuerda)
    "fuerza": 40.0,          # N por fibra (igual que v0: P4 = 160 N con 4, P3 = 120 N con 3)
    "rpm_salida": 4200,      # motor ~17 000 rpm / 4
    "masa_g": 9.5,           # masa real estimada de motor + reductora + encoder (catálogo clase Ø10)
}
# posiciones (x, a) de las fibras alrededor del eje del pack; varilla guía en el centro
PACK_V1 = {
    "P4": {"fibras": [(5.6, 5.6), (-5.6, 5.6), (-5.6, -5.6), (5.6, -5.6)], "demo": "M07"},
    "P3": {"fibras": [(0.0, 6.5), (-5.63, -3.25), (5.63, -3.25)], "demo": "M12"},
}
R_VARILLA = 0.75              # varilla guía de fibra de carbono Ø1,5: impide que la aponeurosis gire
Y_CABEZAL = (-3.0, -27.0)    # cotas de las dos placas que sujetan los motores


def r_pack(pack):
    return max(math.hypot(x, a) for x, a in PACK_V1[pack]["fibras"]) + FIBRA["r_motor"] + 1.0


# ====================================================================== dimensionado
def largo_tendon(m, q):
    T = P.cinematica(q)
    w = []
    for g, p in [(m["grupo"], m["guia"])] + list(m["ruta"]):
        R, t = T[g]
        w.append(P.add(P.mvec(R, P.W(p)), t))
    return sum(P.norm(P.sub(w[i + 1], w[i])) for i in range(len(w) - 1))


def excursiones(n=20000, semilla=1):
    """Recorrido del tendón (máx - mín) de cada músculo en todo el rango articular.
    Ruta en línea recta entre guías: es una cota superior (sobre todo en el hombro)."""
    random.seed(semilla)
    A = P.ARTICULACIONES
    res = {m["id"]: [1e9, -1e9] for m in P.MUSCULOS}
    for k in range(n):
        if k < 2 ** len(A):     # primero todas las esquinas del rango
            q = {a["id"]: a["rango"][(k >> i) & 1] for i, a in enumerate(A)}
        else:
            q = {a["id"]: random.uniform(*a["rango"]) for a in A}
        for m in P.MUSCULOS:
            L = largo_tendon(m, q)
            r = res[m["id"]]
            r[0], r[1] = min(r[0], L), max(r[1], L)
    return {k: v[1] - v[0] for k, v in res.items()}


def tsa(L, c):
    """Cuerda retorcida de largo L contraída una fracción c: vueltas, par y relación de transmisión."""
    r, F = FIBRA["r_cuerda"], FIBRA["fuerza"]
    p = L * (1 - c)
    theta = math.sqrt(L * L - p * p) / r                     # rad
    tau = F * theta * r * r / p / 1000.0                      # N·m (mm -> m)
    return {"vueltas": theta / (2 * math.pi), "par_mNm": tau * 1000, "t_s": theta / (2 * math.pi) / (FIBRA["rpm_salida"] / 60)}


def dimensionar():
    exc = excursiones()
    c = FIBRA["contraccion"]
    filas = []
    for m in P.MUSCULOS:
        e = exc[m["id"]]
        L = math.ceil(e / c / 5) * 5 + 10                      # cuerda: recorrido/contracción + margen, a 5 mm
        t = tsa(L, c)
        n = len(PACK_V1[m["pack"]]["fibras"])
        v0 = P.PACK[m["pack"]]
        # ¿cabe la fibra entre el origen actual y la primera guía? (cabezal + cuerda + aponeurosis/muelle)
        necesita = FIBRA["largo_motor"] + FIBRA["largo_cubo"] + L + 20.0
        disponible = P.norm(P.sub(m["guia"], m["O"]))
        falta = necesita - disponible
        if falta <= 0:
            donde = "cabe"
        elif falta <= 85:
            donde = f"subir origen {math.ceil(falta / 5) * 5:.0f} mm"   # como en el cuerpo: el origen va hacia el codo/hombro
        else:
            donde = "cabezal en el torso"
        filas.append({
            "id": m["id"], "nombre": m["nombre"], "pack": m["pack"], "fibras": n,
            "recorrido_mm": round(e, 1), "cuerda_mm": L, "vueltas": round(t["vueltas"], 1),
            "par_mNm": round(t["par_mNm"], 1), "t_contraccion_s": round(t["t_s"], 2),
            "fuerza_N": FIBRA["fuerza"] * n, "motor_en": donde,
            "v0_largo_mm": v0["Lmax"], "v0_diam_mm": 2 * v0["r_disco"],
            "v1_largo_mm": FIBRA["largo_motor"] + FIBRA["largo_cubo"], "v1_diam_mm": round(2 * r_pack(m["pack"]), 1),
        })
    return filas


def imprimir(filas):
    print(f"{'id':4} {'músculo':20} {'pack':4} {'rec.':>6} {'cuerda':>6} {'vueltas':>7} {'par':>5} {'t(s)':>5}  motor")
    for f in filas:
        print(f"{f['id']:4} {f['nombre']:20} {f['pack']:4} {f['recorrido_mm']:6.1f} {f['cuerda_mm']:6d} "
              f"{f['vueltas']:7.1f} {f['par_mNm']:5.1f} {f['t_contraccion_s']:5.2f}  {f['motor_en']}")
    for pk in PACK_V1:
        v0 = P.PACK[pk]
        print(f"pack {pk}: v0 Ø{2 * v0['r_disco']:.0f} x {v0['Lmax']:.0f} mm  ->  v1 Ø{2 * r_pack(pk):.1f} x "
              f"{FIBRA['largo_motor'] + FIBRA['largo_cubo']:.0f} mm")


# ====================================================================== CAD (SolidWorks)
def cad(filas):
    import swx
    from swx import s, Pieza, Ensamble
    from generar import circ, rect

    swx.COLOR.update({"motor": (0.16, 0.18, 0.22), "cubo": (0.75, 0.55, 0.25),
                      "funda": (0.90, 0.92, 0.95), "carbono": (0.10, 0.10, 0.11)})
    os.makedirs(os.path.join(SAL, "stl"), exist_ok=True)
    swx.iniciar()
    F = FIBRA
    y_cubo = -F["largo_motor"]
    y_cuerda = y_cubo - F["largo_cubo"]
    reg, piezas = {}, {}

    def guardar(info, nombre):
        reg[nombre] = {"masa_g": info["masa_g"], "color": info["color"]}
        piezas[nombre] = info["ruta"]

    # -- fibra: motor (una pieza, se repite en cada posición)
    p = Pieza("fibra_motor", SAL)
    rm = F["r_motor"]
    p.rev("y", 0, 0, [(2.0, 1.8), (0.0, 1.8), (0.0, rm - 0.6), (-0.6, rm), (-4.0, rm), (-4.0, rm - 0.35),
                      (-5.0, rm - 0.35), (-5.0, rm), (y_cubo + 2.0, rm), (y_cubo, rm - 1.4), (y_cubo, 0.0)],
          nombre="Carcasa_motor_reductora")
    guardar(p.terminar("motor", "Aleación 6061"), "fibra_motor")

    p = Pieza("fibra_cubo", SAL)
    p.rev("y", 0, 0, [(y_cubo, 2.6), (y_cuerda + 1.0, 2.6), (y_cuerda, 1.6), (y_cuerda, 0.0)], nombre="Cubo_salida")
    p.taladro("frontal", [circ(0, y_cubo - 2.0, 0.5)], nombre="Paso_cuerda")
    guardar(p.terminar("cubo", "AISI 304"), "fibra_cubo")

    for pk, d in PACK_V1.items():
        fila = next(f for f in filas if f["id"] == d["demo"])
        L = fila["cuerda_mm"]
        y_apo = y_cuerda - L                       # aponeurosis en reposo (cuerda sin retorcer)
        rp = r_pack(pk)

        p = Pieza(f"fibra_cuerda_{pk}", SAL)
        p.rev("y", 0, 0, [(y_cuerda, F["r_haz"]), (y_apo, F["r_haz"])], nombre="Cuerdas_UHMWPE")
        guardar(p.terminar("tendon", "Polietileno reticulado"), f"fibra_cuerda_{pk}")

        ri, re = F["funda"]
        y_f0, y_f1 = y_cuerda - 3.0, y_apo + fila["recorrido_mm"] + 6.0   # la funda deja libre la carrera
        p = Pieza(f"fibra_funda_{pk}", SAL)
        p.rev("y", 0, 0, [(y_f0, ri), (y_f0, re), (y_f1, re), (y_f1, ri)], anillo=True, nombre="Funda_PTFE")
        guardar(p.terminar("funda", "PTFE (general)"), f"fibra_funda_{pk}")

        # placa del cabezal (se usa dos veces): sujeta los motores y lleva la pata al hueso
        p = Pieza(f"cabezal_{pk}", SAL)
        ents = [circ(0, 0, rp)] + [circ(x, a, rm + 0.05) for x, a in d["fibras"]] + [circ(0, 0, R_VARILLA + 0.05)]
        p.ext("superior", ents, -2.0, 2.0, nombre="Placa_cabezal")
        p.ext("superior", [rect(-(rp + 6), -4.5, -(rp - 1.5), 4.5)], -2.0, 2.0, nombre="Pata_al_hueso")
        guardar(p.terminar("soporte", "Nailon 101"), f"cabezal_{pk}")

        # aponeurosis deslizante: ata las cuerdas, corre por la varilla y tira del muelle/tendón
        p = Pieza(f"aponeurosis_v1_{pk}", SAL)
        ents = [circ(0, 0, rp - 2.0), circ(0, 0, R_VARILLA + 0.15)] + [circ(x, a, 0.6) for x, a in d["fibras"]]
        p.ext("superior", ents, y_apo - 3.0, y_apo, nombre="Disco_aponeurosis")
        p.rev("y", 0, 0, [(y_apo - 3.0, 3.0), (y_apo - 9.0, 3.0), (y_apo - 9.0, 1.2)], nombre="Boca_tendon")
        guardar(p.terminar("ancla", "Aleación 6061"), f"aponeurosis_v1_{pk}")

        p = Pieza(f"varilla_guia_{pk}", SAL)
        p.rev("y", 0, 0, [(Y_CABEZAL[0] + 2.0, R_VARILLA), (y_apo - 14.0, R_VARILLA)],
              nombre="Varilla_carbono")
        guardar(p.terminar("carbono", "Nailon 101"), f"varilla_guia_{pk}")

        # pack completo
        e = Ensamble(f"Pack_v1_{pk}", SAL)
        comp = []
        for x, a in d["fibras"]:
            t = (x, 0.0, -a)                            # (X, Y, Z) de SolidWorks: Z = -a
            for n in ("fibra_motor", "fibra_cubo", f"fibra_cuerda_{pk}", f"fibra_funda_{pk}"):
                e.poner(piezas[n], None, t); comp.append((n, t))
        for yc in Y_CABEZAL:
            e.poner(piezas[f"cabezal_{pk}"], None, (0.0, yc, 0.0)); comp.append((f"cabezal_{pk}", (0.0, yc, 0.0)))
        for n in (f"aponeurosis_v1_{pk}", f"varilla_guia_{pk}"):
            e.poner(piezas[n], None, (0.0, 0.0, 0.0)); comp.append((n, (0.0, 0.0, 0.0)))
        e.guardar()
        e.activar()
        for vista in ("isometrica", "frontal", "derecha"):
            try:
                with open(os.path.join(SAL, f"pack_{pk}_{vista}.png"), "wb") as f:
                    f.write(s.captura(vista, 900, 1100))
            except Exception as ex:  # noqa: BLE001
                print("  aviso: captura", vista, ex)
        reg[f"_pack_{pk}"] = {"componentes": comp, "cuerda_mm": L, "y_apo": y_apo,
                              "recorrido_mm": fila["recorrido_mm"], "demo": d["demo"]}

    for n, ruta in piezas.items():
        swx.exportar_stl(ruta, os.path.join(SAL, "stl", n + ".stl"))
    json.dump(reg, open(os.path.join(SAL, "registro_piezas.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  piezas:", ", ".join(f"{k} {v['masa_g']} g" for k, v in reg.items() if not k.startswith("_")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cad", action="store_true", help="generar también las piezas en SolidWorks")
    a = ap.parse_args()
    os.makedirs(SAL, exist_ok=True)
    filas = dimensionar()
    imprimir(filas)
    json.dump({"fibra": FIBRA, "packs": {k: {"fibras": v["fibras"], "r_pack": round(r_pack(k), 2)} for k, v in PACK_V1.items()},
               "musculos": filas}, open(os.path.join(SAL, "dimensionado.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    if a.cad:
        cad(filas)


if __name__ == "__main__":
    main()
