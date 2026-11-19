"""Genera el brazo biomimético v0 en SolidWorks 2020 a partir de param.py.

Uso (desde la carpeta del proyecto):
    solidworks-mcp\\.venv\\Scripts\\python.exe cad\\generador\\generar.py            -> todo
    ... generar.py --pieza humero                                              -> una pieza y su captura
    ... generar.py --desde grupos                                              -> reutiliza las piezas ya hechas

Salida en cad/brazo_v0/: piezas .SLDPRT, subensambles .SLDASM, Brazo_biomimetico_v0.SLDASM,
stl/ (una malla por pieza) y modelo.json (estructura, articulaciones y músculos para el simulador).
"""
import argparse
import json
import math
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import param as P
import swx
from swx import s, Pieza, Ensamble

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAL = os.path.join(RAIZ, "brazo_v0")
STL = os.path.join(SAL, "stl")
REG = os.path.join(SAL, "registro_piezas.json")
W = P.W


def poli(pts):
    return {"tipo": "polilinea", "puntos": pts}


def rect(x1, y1, x2, y2):
    return poli([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])


def circ(x, y, r):
    return {"tipo": "circulo", "x": x, "y": y, "r": r}


# ====================================================================== piezas
def humero():
    p = Pieza("humero", SAL)
    xs = P.X_DIAF
    p.rev("y", xs, 0, [(-12, 12.5), (-30, 12.4), (-52, 11.2), (-120, 10.3), (-200, 10.6), (-238, 11.6), (-252, 11.8)],
          curva=True, nombre="Diafisis")
    p.esfera((0, 0, 0), 22, "Cabeza_humeral")
    p.esfera((20, -10, 0), 8, "Tuberculo_mayor")
    p.esfera((9, -12, 17), 6, "Tuberculo_menor")
    p.esfera((17.5, -125, 0), 4.5, "Tuberosidad_deltoidea")
    paleta = [(-2, -236), (20, -236), (33, -278), (36, -288), (31, -297), (-14, -297), (-29, -294), (-31, -286), (-20, -276)]
    p.ext("frontal", [poli(paleta)], -8, 3, nombre="Paleta_distal")
    p.ext("frontal", [rect(-8.5, -300, 8.5, -268)], -9, 4, corte=True, nombre="Fosa_olecraneana")
    p.ext("frontal", [rect(9.5, -294, 36.5, -272)], -2, 4, corte=True, nombre="Fosa_radial")
    p.rev("x", -300, 0, [(-11, 12), (-6, 10.6), (0, 10), (6, 10.6), (11, 12)], nombre="Troclea")
    p.esfera((P.C_CAP[0], -300, 0), 10.5, "Capitulo")
    p.taladro("lateral", [circ(0, -300, 3.05)], nombre="Agujero_eje_codo")
    return p.terminar("hueso", "Nailon 101")


def eje_codo():
    p = Pieza("eje_codo", SAL)
    p.rev("x", 0, 0, [(-14, 4.5), (-12.5, 4.5), (-12.5, 3), (34, 3), (34, 4.5), (35.5, 4.5)], nombre="Pasador_codo")
    return p.terminar("acero", "AISI 304")


def cubito_gancho():
    p = Pieza("cubito_gancho", SAL)
    c, sn = lambda r, g: r * math.cos(math.radians(g)), lambda r, g: r * math.sin(math.radians(g))
    ro, ri, g0, g1, gm = 19.0, 12.6, 130.0, 285.0, 207.5
    ents = [
        {"tipo": "arco3", "x1": c(ro, g0), "y1": sn(ro, g0), "x2": c(ro, g1), "y2": sn(ro, g1), "x3": c(ro, gm), "y3": sn(ro, gm)},
        {"tipo": "arco3", "x1": c(ri, g0), "y1": sn(ri, g0), "x2": c(ri, g1), "y2": sn(ri, g1), "x3": c(ri, gm), "y3": sn(ri, gm)},
        {"tipo": "linea", "x1": c(ro, g1), "y1": sn(ro, g1), "x2": c(ri, g1), "y2": sn(ri, g1)},
        {"tipo": "linea", "x1": c(ri, g0), "y1": sn(ri, g0), "x2": c(ro, g0), "y2": sn(ro, g0)},
    ]
    p.ext("lateral", ents, -7, 7, nombre="Gancho_troclear")
    p.ext("lateral", [circ(c(21, 140), sn(21, 140), 6.5)], -7, 7, nombre="Olecranon")
    p.ext("lateral", [circ(6, -20, 5.5)], -6, 6, nombre="Coronoides")
    return p.terminar("hueso", "Nailon 101")


L_CUBITO = P.norm(P.sub(P.UT, P.P2))


def cubito_diafisis():
    """Marco propio: origen en el centro de la cabeza del cúbito; la diáfisis sube por +Y local."""
    p = Pieza("cubito_diafisis", SAL)
    L = L_CUBITO
    p.rev("y", 0, 0, [(-8, 4.5), (-6, 7.5), (6, 7.5), (9, 5.8), (70, 5.6), (150, 6.4), (L, 7.5)], nombre="Diafisis_y_cabeza")
    p.esfera((0, L, 0), 7.5, "Extremo_proximal")
    return p.terminar("hueso", "Nailon 101")


def rodamiento_anular():
    p = Pieza("rodamiento_anular", SAL)
    p.rev("y", 0, 0, [(-4, 10.4), (-4, 12.2), (4, 12.2), (4, 10.4)], anillo=True, nombre="Anillo")
    return p.terminar("acero", "AISI 304")


def cabeza_radial():
    """Marco propio: a lo largo de -Y local (eje de pronosupinación). Cabeza, cuello y tambor de tendones."""
    p = Pieza("cabeza_radial", SAL)
    p.rev("y", 0, 0, [(3.5, 9.8), (-3.5, 9.8), (-5, 6.3), (-15, 6.3), (-16, 10.5), (-18, 10.5), (-18, 9), (-38, 9),
                      (-38, 10.5), (-40, 10.5), (-41, 6.5), (-50, 6.5)], nombre="Cabeza_cuello_tambor")
    p.esfera((0, -50, 0), 6.5, "Union_diafisis")
    return p.terminar("hueso", "Nailon 101")


def segmento(nombre, L, r0, r1):
    p = Pieza(nombre, SAL)
    p.rev("y", 0, 0, [(0, r0), (-L, r1)], nombre="Diafisis")
    p.esfera((0, 0, 0), r0, "Union_proximal")
    p.esfera((0, -L, 0), r1, "Union_distal")
    return p.terminar("hueso", "Nailon 101")


L_RADIO1 = P.norm(P.sub(P.R1, P.R0))
L_RADIO2 = P.norm(P.sub(P.R2, P.R1))


def radio_distal():
    """Pieza del grupo G3 con origen propio en el centro de la muñeca."""
    g = P.g2a3
    p = Pieza("radio_distal", SAL, origen=P.W_G3)
    cuerpo = [(19.5, -204), (45, -204), (47.5, -226), (46.5, -241), (7.5, -241), (7.5, -238.5), (19.5, -238.5)]
    p.ext("frontal", [poli([g((x, y, 0))[:2] for x, y in cuerpo])], -9, 9, nombre="Epifisis_distal")
    wy = P.W_G3[1]
    oreja = [{"tipo": "ranura", "x1": 0, "y1": wy + 15, "x2": 0, "y2": wy, "ancho": 16}]
    p.ext("lateral", oreja, g((7.5, 0, 0))[0], g((11.5, 0, 0))[0], nombre="Oreja_medial")
    p.ext("lateral", oreja, g((42.5, 0, 0))[0], g((46.5, 0, 0))[0], nombre="Oreja_lateral")
    p.taladro("lateral", [circ(0, wy, 2.6)], nombre="Agujero_eje_muneca")
    return p.terminar("hueso", "Nailon 101")


def cruceta():
    p = Pieza("cruceta_muneca", SAL)
    p.ext("frontal", [rect(-6, -6, 6, 6)], -6, 6, nombre="Nucleo")
    p.rev("x", 0, 0, [(-21, 2.5), (21, 2.5)], nombre="Eje_flexion")
    p.rev("a", 0, 0, [(-14.5, 2.5), (14.5, 2.5)], nombre="Eje_desviacion")
    return p.terminar("acero", "AISI 304")


def adaptador_mano():
    p = Pieza("adaptador_mano", SAL)
    oreja = [{"tipo": "ranura", "x1": 0, "y1": 0, "x2": 0, "y2": -16, "ancho": 14}]
    p.ext("frontal", oreja, 9.5, 12.5, nombre="Oreja_anterior")
    p.ext("frontal", oreja, -12.5, -9.5, nombre="Oreja_posterior")
    p.ext("frontal", [rect(-9, -23, 9, -15)], -12.5, 12.5, nombre="Puente")
    p.rev("y", 0, 0, [(-21, 11), (-22, 24), (-27, 24), (-27, 11)], nombre="Brida_mano")
    p.taladro("frontal", [circ(0, 0, 2.6)], nombre="Agujero_eje_desviacion")
    return p.terminar("aluminio", "Aleación 6061")


def mano_ref():
    p = Pieza("mano_referencia", SAL)
    palma = [(-36, -27), (36, -27), (40, -60), (38, -118), (-38, -118), (-40, -60)]
    p.ext("frontal", [poli(palma)], -11, 11, nombre="Palma")
    for i, (x, L) in enumerate([(-28.5, 60), (-9.5, 76), (9.5, 84), (28.5, 74)]):
        p.ext("frontal", [{"tipo": "ranura", "x1": x, "y1": -112, "x2": x, "y2": -118 - L, "ancho": 16.5}], -8, 8,
              nombre=["Menique", "Anular", "Medio", "Indice"][i])
    p.ext("frontal", [{"tipo": "ranura", "x1": 36, "y1": -62, "x2": 64, "y2": -102, "ancho": 18}], -3, 13, nombre="Pulgar")
    return p.terminar("mano", "ABS")


def montura_hombro():
    p = Pieza("montura_hombro", SAL)
    techo = [(-172, -60), (16, -60), (36, -18), (36, 18), (16, 60), (-172, 60)]
    p.ext("superior", [poli(techo)], 38.5, 42, nombre="Placa_superior_acromion")
    p.ext("frontal", [poli([(-172, 40), (-10, 40), (-10, -22), (-22, -86), (-172, -86)])], -30, -26.5, nombre="Placa_posterior_escapula")
    p.ext("frontal", [poli([(-150, 40), (-10, 40), (-10, -24), (-150, -24)])], 26.5, 30, nombre="Placa_anterior")
    p.ext("frontal", [rect(-36, 20, -14, 40)], -27, 27, nombre="Cuello_glenoideo")
    R = 22.6
    copa = [(-36, 27.5), (-12, 27.5)] + [(-R * math.cos(math.radians(t)), R * math.sin(math.radians(t))) for t in (58.6, 45, 30, 15)] + [(-R, 0)]
    p.rev("x", 0, 0, copa, nombre="Cavidad_glenoidea")
    # ventanas de aligeramiento entre los músculos
    p.ext("frontal", [rect(-160, -34, -40, 22)], -31, -25, corte=True, nombre="Ventana_posterior")
    p.ext("frontal", [rect(-140, -16, -40, 10)], 25, 31, corte=True, nombre="Ventana_anterior")
    return p.terminar("montura", "Nailon 101")


def unidad(tam):
    r, L = P.UNIDAD[tam]
    k = L * 0.42
    p = Pieza(f"unidad_motora_{tam}", SAL)
    p.rev("y", 0, 0, [(0, r * 0.55), (-2, r), (-k, r), (-k - 1, r - 1.1), (-k - 4, r - 1.1), (-k - 5, r - 0.5),
                      (-L + 4, r - 0.5), (-L, r * 0.4)], nombre="Motor_reductora_husillo")
    return p.terminar("u" + tam, "Ti-6Al-4V")


def separador(pack):
    d = P.PACK[pack]
    p = Pieza(f"separador_{pack}", SAL)
    ents = [circ(0, 0, d["r_disco"])]
    for tam, (lx, ly, lz) in d["unidades"]:
        ents.append(circ(lx, -lz, P.UNIDAD[tam][0] + 0.15))
    p.ext("superior", ents, -2, 2, nombre="Disco_separador")
    p.ext("superior", [rect(-(d["r_disco"] + 5), -5, -(d["r_disco"] - 2), 5)], -2, 2, nombre="Pata_al_hueso")
    return p.terminar("soporte", "Aleación 6061")


def aponeurosis(pack):
    d = P.PACK[pack]
    p = Pieza(f"aponeurosis_{pack}", SAL)
    p.rev("y", 0, 0, [(0, d["r_apo"][0]), (-d["apo"], d["r_apo"][1])], nombre="Cono_de_union")
    return p.terminar("tendon", "Nailon 101")


def resorte(pack):
    d = P.PACK[pack]
    L, (ra, rb) = d["resorte"], d["r_res"]
    pts = [(0, rb * 0.7)]
    n = int(L // 2)
    for i in range(n):
        y = -(i * L / n)
        pts += [(y - L / n * 0.25, ra), (y - L / n * 0.75, rb)]
    pts.append((-L, rb * 0.7))
    p = Pieza(f"resorte_serie_{pack}", SAL)
    p.rev("y", 0, 0, pts, nombre="Elemento_elastico_en_serie")
    return p.terminar("resorte", "AISI 304")


def tendon(pack, T):
    r = P.PACK[pack]["r_tendon"]
    p = Pieza(nombre_tendon(pack, T), SAL)
    p.rev("y", 0, 0, [(0, r), (-T, r)], nombre="Tendon")
    return p.terminar("tendon", "Nailon 101")


def nombre_tendon(pack, T):
    return f"tendon_{pack}_{int(round(T)):03d}"


def guia(pack):
    r = P.PACK[pack]["r_tendon"]
    p = Pieza(f"guia_tendon_{pack}", SAL)
    p.rev("y", 0, 0, [(-3, r + 0.6), (-3, r + 2.6), (3, r + 2.6), (3, r + 0.6)], anillo=True, nombre="Ojal_guia")
    return p.terminar("guia", "AISI 304")


def ancla():
    p = Pieza("ancla_tendon", SAL)
    p.rev("y", 0, 0, [(3.2, 0), (2.3, 2.3), (0, 3.2), (-2.3, 2.3), (-2.9, 1.5), (-8, 1.5)], nombre="Ancla_de_insercion")
    return p.terminar("ancla", "AISI 304")


def catalogo():
    c = {
        "humero": humero, "eje_codo": eje_codo, "cubito_gancho": cubito_gancho, "cubito_diafisis": cubito_diafisis,
        "rodamiento_anular": rodamiento_anular, "cabeza_radial": cabeza_radial,
        "radio_diafisis_1": lambda: segmento("radio_diafisis_1", L_RADIO1, 6.5, 6.8),
        "radio_diafisis_2": lambda: segmento("radio_diafisis_2", L_RADIO2, 6.8, 7.5),
        "radio_distal": radio_distal, "cruceta_muneca": cruceta, "adaptador_mano": adaptador_mano,
        "mano_referencia": mano_ref, "montura_hombro": montura_hombro, "ancla_tendon": ancla,
    }
    for t in "SML":   # nota: «Ti-6Al-4V» no existe con ese nombre en la biblioteca de SW 2020; quedan sin material
        c[f"unidad_motora_{t}"] = (lambda t=t: unidad(t))
    for k in P.PACK:
        c[f"separador_{k}"] = (lambda k=k: separador(k))
        c[f"aponeurosis_{k}"] = (lambda k=k: aponeurosis(k))
        c[f"resorte_serie_{k}"] = (lambda k=k: resorte(k))
        c[f"guia_tendon_{k}"] = (lambda k=k: guia(k))
    for m in P.MUSCULOS:
        c[nombre_tendon(m["pack"], m["T"])] = (lambda m=m: tendon(m["pack"], m["T"]))
    return c


def ruta_pieza(nombre):
    return os.path.join(SAL, nombre + ".SLDPRT")


def hacer_piezas(solo=None, faltan=False):
    reg = json.load(open(REG, encoding="utf-8")) if os.path.exists(REG) else {}
    fallos = []
    for nombre, fn in catalogo().items():
        if solo and nombre not in solo:
            continue
        if faltan and nombre in reg and os.path.exists(ruta_pieza(nombre)):
            continue
        t0 = time.time()
        try:
            info = fn()
            reg[nombre] = {"masa_g": info["masa_g"], "color": list(info["color"])}
        except Exception:  # noqa: BLE001
            fallos.append(nombre)
            print(f"[FALLO] pieza {nombre}")
            traceback.print_exc(limit=3)
        print(f"    ({time.time() - t0:.1f} s)")
        json.dump(reg, open(REG, "w", encoding="utf-8"), indent=1)
    return fallos


# ====================================================================== músculos (subensambles)
def contenido_musculo(m):
    """Lista de (pieza, traslación local SW) dentro del subensamble del músculo."""
    d = P.PACK[m["pack"]]
    items = []
    for tam, (lx, ly, lz) in d["unidades"]:
        items.append((f"unidad_motora_{tam}", (lx, -(d["Lmax"] - P.UNIDAD[tam][1]), lz)))
    for ys in d["separadores"]:
        items.append((f"separador_{m['pack']}", (0.0, ys, 0.0)))
    y = -d["Lmax"]
    items.append((f"aponeurosis_{m['pack']}", (0.0, y, 0.0)))
    y -= d["apo"]
    items.append((f"resorte_serie_{m['pack']}", (0.0, y, 0.0)))
    y -= d["resorte"]
    items.append((nombre_tendon(m["pack"], m["T"]), (0.0, y, 0.0)))
    items.append((f"guia_tendon_{m['pack']}", (0.0, y - m["T"] + 3.0, 0.0)))
    return items


def nombre_musculo(m):
    return f"{m['id']}_{m['nombre']}"


def hacer_musculos():
    for m in P.MUSCULOS:
        e = Ensamble(nombre_musculo(m), SAL)
        for pieza, t in contenido_musculo(m):
            e.poner(ruta_pieza(pieza), None, t)
        e.guardar()
        print(f"  músculo {e.nombre}: {len(contenido_musculo(m))} componentes")


def marco_musculo(m):
    return P.marco_hacia(W(m["d"]), W(m["n"])), W(m["O"])


# ====================================================================== grupos
def contenido_grupos():
    """{grupo: [(archivo sin extensión, tipo 'pieza'|'musculo', R, t, etiqueta)]} en coordenadas SW del grupo."""
    I = None
    g = {k: [] for k in P.GRUPOS}
    g["G0"].append(("montura_hombro", "pieza", I, (0, 0, 0), "montura"))
    g["G1"] += [("humero", "pieza", I, (0, 0, 0), "humero"), ("eje_codo", "pieza", I, W(P.E_G1), "eje_codo")]
    dir_cub = P.unit(P.sub(P.P2, P.UT))
    g["G2"] += [("cubito_gancho", "pieza", I, (0, 0, 0), "gancho"),
                ("cubito_diafisis", "pieza", P.marco_hacia(W(dir_cub)), W(P.P2), "diafisis"),
                ("rodamiento_anular", "pieza", P.marco_hacia(W(P.U_PRONO)), W(P.P1), "anular")]
    g["G3"] += [("cabeza_radial", "pieza", P.marco_hacia(W(P.U_PRONO)), (0, 0, 0), "cabeza"),
                ("radio_diafisis_1", "pieza", P.marco_hacia(W(P.sub(P.R1, P.R0))), W(P.R0), "radio1"),
                ("radio_diafisis_2", "pieza", P.marco_hacia(W(P.sub(P.R2, P.R1))), W(P.R1), "radio2"),
                ("radio_distal", "pieza", I, W(P.W_G3), "distal")]
    g["G4"].append(("cruceta_muneca", "pieza", I, (0, 0, 0), "cruceta"))
    g["G5"] += [("adaptador_mano", "pieza", I, (0, 0, 0), "adaptador"), ("mano_referencia", "pieza", I, (0, 0, 0), "mano")]
    for m in P.MUSCULOS:
        R, t = marco_musculo(m)
        g[m["grupo"]].append((nombre_musculo(m), "musculo", R, t, m["id"]))
        ag, ap, ad = m["ancla"]
        g[ag].append(("ancla_tendon", "pieza", P.marco_hacia(W(ad)), W(ap), "ancla_" + m["id"]))
    return g


NOMBRE_GRUPO = {k: f"{k}_{v[0]}" for k, v in P.GRUPOS.items()}


def hacer_grupos():
    cont = contenido_grupos()
    for gid, items in cont.items():
        if gid == "G4":
            continue                                   # la cruceta entra como pieza suelta
        e = Ensamble(NOMBRE_GRUPO[gid], SAL)
        for archivo, tipo, R, t, _ in items:
            ruta = ruta_pieza(archivo) if tipo == "pieza" else os.path.join(SAL, archivo + ".SLDASM")
            e.poner(ruta, R, t)
        e.guardar()
        print(f"  grupo {e.nombre}: {len(items)} componentes")


# ====================================================================== ensamble superior
def _nombre_punto(e, comp):
    """Nombre de selección del punto de origen de un componente (de primer nivel o anidado)."""
    orig = e.origen(comp).Name
    top = e.titulo.rsplit(".", 1)[0]
    partes = comp.Name2.split("/")
    if len(partes) == 1:
        return f"Point1@{orig}@{partes[0]}@{top}"
    return f"Point1@{orig}@{partes[0]}@{top}/{partes[1]}@{partes[0].rsplit('-', 1)[0]}"


def punto_en_plano(e, comp_punto, comp_plano, cual, nombre):
    e.md.ClearSelection2(True)
    n = _nombre_punto(e, comp_punto)
    if not e.md.Extension.SelectByID2(n, "EXTSKETCHPOINT", 0, 0, 0, False, 1, None, 0):
        raise RuntimeError(f"No se pudo seleccionar {n}")
    if not e.plano(comp_plano, cual).Select2(True, 1):
        raise RuntimeError(f"No se pudo seleccionar el plano {cual} de {comp_plano.Name2}")
    r = e.asm.AddMate5(0, 2, False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False, False, 0)
    m = r[0] if isinstance(r, tuple) else r
    e.md.ClearSelection2(True)
    if m is None:
        raise RuntimeError(f"Relación {nombre} falló: {r}")
    try:
        s.cast(m, "IFeature").Name = nombre
    except Exception:  # noqa: BLE001
        pass


def punto_fijo(e, comp_punto, comp_planos, nombre):
    for cual in ("frontal", "superior", "lateral"):
        punto_en_plano(e, comp_punto, comp_planos, cual, f"{nombre}_{cual}")


def hacer_brazo(pose=None, nombre="Brazo_biomimetico_v0"):
    pose = pose or P.POSE_REF
    T = P.cinematica(pose)
    e = Ensamble(nombre, SAL)
    c = {}
    for gid in P.GRUPOS:
        ruta = ruta_pieza("cruceta_muneca") if gid == "G4" else os.path.join(SAL, NOMBRE_GRUPO[gid] + ".SLDASM")
        R, t = T[gid]
        c[gid] = e.poner(ruta, R, t, fijo=(gid == "G0"), alias=gid)
    n1, n2, n3 = (c[g].Name2 for g in ("G1", "G2", "G3"))
    eje_codo_c = e.componente(f"{n1}/eje_codo")
    anular_c = e.componente(f"{n2}/rodamiento_anular")
    cubito_c = e.componente(f"{n2}/cubito_diafisis")
    cabeza_c = e.componente(f"{n3}/cabeza_radial")
    distal_c = e.componente(f"{n3}/radio_distal")
    pasos = [
        ("hombro (rótula, 3 giros)", lambda: punto_fijo(e, c["G1"], c["G0"], "Hombro_rotula")),
        ("codo: centro", lambda: punto_fijo(e, c["G2"], eje_codo_c, "Codo_centro")),
        ("codo: bisagra", lambda: e.relacion("paralelo", e.plano(c["G2"], "lateral"), e.plano(c["G1"], "lateral"), "Codo_bisagra")),
        ("antebrazo: cabeza del radio", lambda: punto_fijo(e, c["G3"], anular_c, "Radio_cabeza")),
        ("antebrazo: pivote cubital 1", lambda: punto_en_plano(e, cubito_c, cabeza_c, "frontal", "Radio_pivote_frontal")),
        ("antebrazo: pivote cubital 2", lambda: punto_en_plano(e, cubito_c, cabeza_c, "lateral", "Radio_pivote_lateral")),
        ("muñeca: centro flexión", lambda: punto_fijo(e, c["G4"], distal_c, "Muneca_centro")),
        ("muñeca: bisagra flexión", lambda: e.relacion("paralelo", e.plano(c["G4"], "lateral"), e.plano(c["G3"], "lateral"), "Muneca_flexion")),
        ("muñeca: centro desviación", lambda: punto_fijo(e, c["G5"], c["G4"], "Mano_centro")),
        ("muñeca: bisagra desviación", lambda: e.relacion("paralelo", e.plano(c["G5"], "frontal"), e.plano(c["G4"], "frontal"), "Muneca_desviacion")),
    ]
    fallos = []
    for nombre_paso, fn in pasos:
        try:
            fn()
            print(f"  relación OK: {nombre_paso}")
        except Exception as ex:  # noqa: BLE001
            fallos.append(nombre_paso)
            print(f"  [FALLO] relación {nombre_paso}: {ex}")
    e.md.EditRebuild3()
    e.guardar()
    # comprobar que las relaciones no movieron nada
    for gid in P.GRUPOS:
        R, t = T[gid]
        real = [v * 1000 for v in c[gid].Transform2.ArrayData[9:12]]
        err = max(abs(real[i] - t[i]) for i in range(3))
        print(f"  {gid}: desplazamiento respecto a la pose pedida = {err:.3f} mm")
    try:
        info = s.masa(e.md)
        print(f"  MASA TOTAL: {info['masa_g']:.0f} g; centro de masa {info['centro_masa_mm']}")
    except Exception as ex:  # noqa: BLE001
        info = None
        print("  aviso: masa total no calculada:", ex)
    return e, fallos, info


def capturas(e, prefijo):
    e.activar()
    for vista in ("isometrica", "posterior", "derecha", "frontal"):
        try:
            with open(os.path.join(SAL, f"{prefijo}_{vista}.png"), "wb") as f:
                f.write(s.captura(vista, 1100, 1300))
        except Exception as ex:  # noqa: BLE001
            print("  aviso: captura", vista, ex)


# ====================================================================== exportación
def exportar():
    os.makedirs(STL, exist_ok=True)
    reg = json.load(open(REG, encoding="utf-8"))
    for nombre in reg:
        try:
            swx.exportar_stl(ruta_pieza(nombre), os.path.join(STL, nombre + ".stl"))
        except Exception as ex:  # noqa: BLE001
            print(f"  [FALLO] STL {nombre}: {ex}")
    plano = lambda R: [list(f) for f in (R or P.IDENT)]
    cont = contenido_grupos()
    grupos = []
    for gid, (nom, padre) in P.GRUPOS.items():
        inst = []
        for archivo, tipo, R, t, etiqueta in cont[gid]:
            R = R or P.IDENT
            if tipo == "pieza":
                inst.append({"pieza": archivo, "R": plano(R), "t": list(t), "de": etiqueta})
            else:
                m = next(x for x in P.MUSCULOS if nombre_musculo(x) == archivo)
                for pieza, tl in contenido_musculo(m):
                    inst.append({"pieza": pieza, "R": plano(R), "t": list(P.add(t, P.mvec(R, tl))), "de": m["id"]})
        grupos.append({"id": gid, "nombre": nom, "padre": padre, "origen_en_padre": list(W(P.ORIGEN_EN_PADRE[gid])),
                       "instancias": inst})
    musculos = []
    for m in P.MUSCULOS:
        d = P.PACK[m["pack"]]
        musculos.append({
            "id": m["id"], "nombre": m["nombre"], "grupo": m["grupo"], "paquete": m["pack"],
            "unidades": [t for t, _ in d["unidades"]], "accion": m["accion"], "copia_a": m["copia"],
            "origen": list(W(m["O"])), "direccion": list(W(m["d"])), "largo_paquete": d["largo"], "tendon_interior": m["T"],
            "ruta": [{"grupo": g, "p": list(W(p))} for g, p in m["ruta"]],
        })
    modelo = {
        "nombre": "Brazo biomimético v0", "unidades": "mm",
        "convenio": "Brazo derecho. X = lateral, Y = arriba, Z = posterior (la persona mira hacia -Z). "
                    "Cada instancia se coloca en su grupo con p_grupo = R * p_pieza + t.",
        "piezas": {n: {"stl": f"stl/{n}.stl", "color": v["color"], "masa_g": v["masa_g"]} for n, v in reg.items()},
        "grupos": grupos,
        "articulaciones": [dict(a, eje=list(a["eje"]), rango=list(a["rango"])) for a in P.ARTICULACIONES],
        "pose_foto": P.POSE_FOTO,
        "musculos": musculos,
        "unidad_motora": {k: {"radio": v[0], "largo": v[1]} for k, v in P.UNIDAD.items()},
    }
    json.dump(modelo, open(os.path.join(SAL, "modelo.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  modelo.json y", len(reg), "STL exportados")


# ====================================================================== principal
ETAPAS = ["piezas", "musculos", "grupos", "brazo", "exportar"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pieza", nargs="*", help="generar solo estas piezas y guardar una captura de cada una")
    ap.add_argument("--desde", choices=ETAPAS, default="piezas")
    ap.add_argument("--hasta", choices=ETAPAS, default="exportar")
    ap.add_argument("--faltan", action="store_true", help="en la etapa de piezas, hacer solo las que aún no existen")
    a = ap.parse_args()
    os.makedirs(SAL, exist_ok=True)
    swx.iniciar()
    t0 = time.time()
    if a.pieza:
        cat = catalogo()
        for n in a.pieza:
            cat[n]()
            with open(os.path.join(SAL, f"_vista_{n}.png"), "wb") as f:
                f.write(s.captura("isometrica", 900, 700))
        return
    i0, i1 = ETAPAS.index(a.desde), ETAPAS.index(a.hasta)
    etapas = ETAPAS[i0:i1 + 1]
    if "piezas" in etapas:
        print("== PIEZAS"); f = hacer_piezas(faltan=a.faltan)
        if f:
            print("PIEZAS CON FALLO:", f); return
    if "musculos" in etapas:
        print("== MÚSCULOS"); hacer_musculos()
    if "grupos" in etapas:
        print("== GRUPOS"); hacer_grupos()
    if "brazo" in etapas:
        print("== BRAZO (pose de referencia)")
        e, fallos, info = hacer_brazo(P.POSE_REF, "Brazo_biomimetico_v0")
        capturas(e, "brazo_ref")
        print("== BRAZO (pose de foto)")
        e2, fallos2, _ = hacer_brazo(P.POSE_FOTO, "Brazo_biomimetico_v0_pose")
        capturas(e2, "brazo_pose")
        if info:
            json.dump(info, open(os.path.join(SAL, "masa_total.json"), "w"), indent=1)
    if "exportar" in etapas:
        print("== EXPORTAR"); exportar()
    print(f"Listo en {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
