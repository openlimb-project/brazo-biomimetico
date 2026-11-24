"""Parámetros del brazo biomimético v0 (única fuente de verdad del modelo).

Coordenadas ANATÓMICAS de cada grupo, en mm, brazo derecho en posición anatómica
(colgando, codo extendido, palma al frente):
    x = lateral (hacia fuera del cuerpo), y = arriba, a = anterior (hacia delante).
En SolidWorks y en el simulador web: X = x, Y = y, Z = -a (la persona mira hacia -Z).

Grupos rígidos (cada uno es un subensamble que se mueve como un bloque):
    G0 hombro   : montura fija (escápula artificial) + músculos M01..M06. Origen: centro del hombro S.
    G1 brazo    : húmero + músculos M07..M11. Origen: S (centro de la cabeza del húmero).
    G2 cubito   : cúbito. Origen: E (centro del codo, sobre el eje de la tróclea).
    G3 radio    : radio + músculos de la muñeca M12..M15. Origen: P1 (centro de la cabeza del radio).
    G4 cruceta  : cruceta de la muñeca. Origen: W (centro de la muñeca).
    G5 mano     : adaptador + mano de referencia. Origen: W.
"""
import math


# ------------------------------------------------------------------ vectores
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return math.sqrt(dot(a, a))
def unit(a):
    n = norm(a)
    return (a[0] / n, a[1] / n, a[2] / n)
def W(p): return (p[0], p[1], -p[2])          # anatómico -> SolidWorks / simulador


IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
def mmul(A, B): return tuple(tuple(sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)) for i in range(3))
def mvec(A, v): return tuple(sum(A[i][k] * v[k] for k in range(3)) for i in range(3))
def mcols(cx, cy, cz): return ((cx[0], cy[0], cz[0]), (cx[1], cy[1], cz[1]), (cx[2], cy[2], cz[2]))


def rot_eje(u, ang):
    c, s, t = math.cos(ang), math.sin(ang), 1 - math.cos(ang)
    x, y, z = u
    return ((t * x * x + c, t * x * y - s * z, t * x * z + s * y),
            (t * x * y + s * z, t * y * y + c, t * y * z - s * x),
            (t * x * z - s * y, t * y * z + s * x, t * z * z + c))


def marco_hacia(direccion, fuera=None):
    """Giro (coordenadas SW) que lleva el eje local -Y a `direccion` y el local +X hacia `fuera`."""
    d = unit(direccion)
    ly = mul(d, -1.0)
    if fuera is None:
        fuera = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 0.0, 1.0)
    f = sub(fuera, mul(ly, dot(fuera, ly)))
    lx = unit(f)
    lz = cross(lx, ly)
    return mcols(lx, ly, lz)


# ------------------------------------------------------------------ esqueleto
L_BRAZO = 300.0                       # centro del hombro -> eje del codo
X_DIAF = 9.0                          # eje de la diáfisis del húmero (la cabeza queda algo medial)
E_G1 = (0.0, -L_BRAZO, 0.0)           # centro del codo en G1

# antebrazo, en G2 (origen E)
C_CAP = (22.0, 0.0, 0.0)              # centro del capítulo (cóndilo lateral), sobre el eje del codo
P2 = (10.0, -228.0, 0.0)              # centro de la cabeza del cúbito (pivote distal)
U_PRONO = unit(sub(P2, C_CAP))        # eje de pronosupinación (apunta hacia distal)
P1 = add(C_CAP, mul(U_PRONO, 14.0))   # centro de la cabeza del radio = origen de G3
UT = (0.0, -15.0, -9.0)               # arranque de la diáfisis del cúbito (dentro del gancho)
W_G2 = (27.0, -256.0, 0.0)            # centro de la muñeca
R0_G2 = add(P1, mul(U_PRONO, 46.0))   # fin del cuello del radio
R1_G2 = (38.0, -90.0, 0.0)            # codo de la diáfisis del radio (curva lateral)
R2_G2 = (38.0, -210.0, 0.0)           # extremo distal de la diáfisis


def g2a3(p): return sub(p, P1)        # punto de G2 expresado en G3


W_G3 = g2a3(W_G2)
R0, R1, R2 = g2a3(R0_G2), g2a3(R1_G2), g2a3(R2_G2)
P2_G3 = g2a3(P2)
E1_PRONO = unit(sub((1.0, 0.0, 0.0), mul(U_PRONO, U_PRONO[0])))   # perpendicular al eje, hacia lateral
E2_PRONO = (0.0, 0.0, 1.0)                                         # perpendicular al eje, hacia anterior


def eje_radio(s):
    """Punto sobre el eje de pronosupinación, en G3, a s mm de la cabeza del radio."""
    return mul(U_PRONO, s)


# ------------------------------------------------------------------ músculos
UNIDAD = {"L": (8.0, 70.0), "M": (6.5, 60.0), "S": (5.0, 50.0)}      # radio, largo
# posiciones locales (x hacia fuera del hueso, y a lo largo, z de lado); todas terminan en y = -Lmax
PACK = {
    "P4": {"unidades": [("L", (-8.5, 0.0, 0.0)), ("M", (4.0, -10.0, 9.5)), ("M", (4.0, -10.0, -9.5)),
                        ("S", (13.5, -20.0, 0.0))],
           "Lmax": 70.0, "separadores": (-26.0, -60.0), "apo": 15.0, "resorte": 22.0,
           "r_disco": 19.5, "r_tendon": 1.3, "r_apo": (17.0, 3.2), "r_res": (4.6, 3.2)},
    "P3": {"unidades": [("M", (-5.5, 0.0, 0.0)), ("S", (5.5, -10.0, 6.5)), ("S", (5.5, -10.0, -6.5))],
           "Lmax": 60.0, "separadores": (-16.0, -52.0), "apo": 12.0, "resorte": 18.0,
           "r_disco": 14.5, "r_tendon": 1.1, "r_apo": (12.5, 2.6), "r_res": (3.8, 2.6)},
}
for _p in PACK.values():
    _p["largo"] = _p["Lmax"] + _p["apo"] + _p["resorte"]


def _polar_humero(R, grados):
    """Posición (x, a) alrededor de la diáfisis del húmero; ángulo desde anterior hacia lateral."""
    g = math.radians(grados)
    return (X_DIAF + R * math.sin(g), R * math.cos(g)), (math.sin(g), 0.0, math.cos(g))


def _polar_radio(R, grados):
    g = math.radians(grados)
    return (R2[0] + R * math.sin(g), R * math.cos(g)), (math.sin(g), 0.0, math.cos(g))


RC4, RC3 = 32.5, 27.5                 # distancia del eje del húmero al centro de cada paquete
(_x7, _a7), _n7 = _polar_humero(RC4, 38.5)
(_x8, _a8), _n8 = _polar_humero(RC4, -38.5)
(_x9, _a9), _n9 = _polar_humero(RC4, 180.0)
(_x10, _a10), _n10 = _polar_humero(RC3, -108.7)
(_x11, _a11), _n11 = _polar_humero(RC3, 108.7)

RC_MUN = 30.0                         # paquetes de la muñeca alrededor de la diáfisis del radio
ANG_MUN = {"M12": 5.0, "M13": 65.0, "M14": 125.0, "M15": 185.0}
Y_MUN = -90.0                         # arranque de los paquetes de la muñeca (G3)
Y_GUIA_MUN = -200.0

_c22, _c28, _c34 = eje_radio(22.0), eje_radio(28.0), eje_radio(34.0)


def _musc(id_, nombre, grupo, pack, O, d, n, guia_en, ruta, ancla, accion, copia):
    """guia_en: valor de la coordenada (a lo largo de d) donde termina el tendón dentro del grupo."""
    eje = max(range(3), key=lambda i: abs(d[i]))
    largo_total = abs(guia_en - O[eje])
    T = largo_total - PACK[pack]["largo"]
    if T < 4:
        raise ValueError(f"{id_}: tendón interior demasiado corto ({T:.1f} mm)")
    G = add(O, mul(d, largo_total))
    return {"id": id_, "nombre": nombre, "grupo": grupo, "pack": pack, "O": O, "d": d, "n": n, "T": round(T, 1),
            "guia": G, "ruta": [(grupo, G)] + ruta + [(ancla[0], ancla[1])], "ancla": ancla,
            "accion": accion, "copia": copia}


Y_PL = 63.5                           # altura del eje de los paquetes sobre la placa superior
MUSCULOS = [
    _musc("M01", "deltoides_anterior", "G0", "P4", (-150.0, Y_PL, 40.0), (1, 0, 0), (0, 1, 0), 16.0,
          [], ("G1", (13.0, -115.0, 10.5), (-0.35, 0.0, -0.94)),
          "Lleva el brazo al frente", "Deltoides anterior y pectoral"),
    _musc("M02", "deltoides_posterior", "G0", "P4", (-150.0, Y_PL, -40.0), (1, 0, 0), (0, 1, 0), 16.0,
          [], ("G1", (13.0, -115.0, -10.5), (-0.35, 0.0, 0.94)),
          "Lleva el brazo atrás", "Deltoides posterior y dorsal ancho"),
    _musc("M03", "deltoides_medio", "G0", "P4", (-150.0, Y_PL, 0.0), (1, 0, 0), (0, 1, 0), 34.0,
          [], ("G1", (23.0, -125.0, 0.0), (-1.0, 0.0, 0.0)),
          "Separa el brazo del cuerpo", "Deltoides medio y supraespinoso"),
    _musc("M04", "aductor", "G0", "P4", (-150.0, -62.0, -51.5), (1, 0, 0), (0, 0, -1), -14.0,
          [], ("G1", (-4.5, -100.0, -3.0), (1.0, 0.0, 0.2)),
          "Acerca el brazo al cuerpo", "Pectoral mayor y dorsal ancho"),
    _musc("M05", "rotador_externo", "G0", "P3", (-122.0, -4.0, -46.5), (1, 0, 0), (0, 0, -1), -12.0,
          [], ("G1", (24.0, -8.0, -9.5), (-0.4, -0.2, 0.9)),
          "Gira el brazo hacia fuera", "Infraespinoso y redondo menor"),
    _musc("M06", "rotador_interno", "G0", "P3", (-122.0, -4.0, 46.5), (1, 0, 0), (0, 0, 1), -12.0,
          [], ("G1", (10.0, -10.0, 24.5), (0.0, 0.0, -1.0)),
          "Gira el brazo hacia dentro", "Subescapular"),
    _musc("M07", "biceps", "G1", "P4", (_x7, -55.0, _a7), (0, -1, 0), _n7, -250.0,
          [("G1", (24.0, -286.0, 17.0)),
           ("G3", add(_c22, add(mul(E1_PRONO, -7.0), mul(E2_PRONO, 7.0))))],
          ("G3", add(_c22, mul(E1_PRONO, -12.0)), E1_PRONO),
          "Dobla el codo y gira la palma hacia arriba", "Bíceps"),
    _musc("M08", "braquial", "G1", "P4", (_x8, -55.0, _a8), (0, -1, 0), _n8, -250.0,
          [("G1", (-3.0, -287.0, 16.0))],
          ("G2", (0.0, -22.0, 11.5), (0.0, 0.3, -1.0)),
          "Dobla el codo sin girar la mano", "Braquial"),
    _musc("M09", "triceps", "G1", "P4", (_x9, -55.0, _a9), (0, -1, 0), _n9, -250.0,
          [], ("G2", (0.0, 16.5, -23.5), (0.0, -0.3, 1.0)),
          "Extiende el codo", "Tríceps"),
    _musc("M10", "pronador", "G1", "P3", (_x10, -125.0, _a10), (0, -1, 0), _n10, -262.0,
          [("G1", (-33.0, -289.0, 3.0)), ("G3", add(_c34, mul(E2_PRONO, 10.0)))],
          ("G3", add(_c34, mul(E1_PRONO, 12.0)), mul(E1_PRONO, -1.0)),
          "Gira la palma hacia abajo", "Pronador redondo"),
    _musc("M11", "supinador", "G1", "P3", (_x11, -125.0, _a11), (0, -1, 0), _n11, -262.0,
          [("G1", (38.0, -291.0, -5.0)), ("G3", add(_c28, mul(E1_PRONO, 10.0)))],
          ("G3", add(_c28, mul(E2_PRONO, 12.0)), (0.0, 0.0, -1.0)),
          "Gira la palma hacia arriba con el codo recto", "Supinador"),
]

_MUN = {
    "M12": ("flexor_radial", (16.0, -20.0, 14.0), (13.0, 1.0, 12.0),
            "Dobla la muñeca y la inclina hacia el pulgar", "Flexor radial del carpo"),
    "M13": ("flexor_cubital", (-16.0, -20.0, 14.0), (-13.0, 1.0, 12.0),
            "Dobla la muñeca y la inclina hacia el meñique", "Flexor cubital del carpo"),
    "M14": ("extensor_radial", (16.0, -20.0, -14.0), (13.0, 1.0, -12.0),
            "Extiende la muñeca hacia el pulgar", "Extensores radiales del carpo"),
    "M15": ("extensor_cubital", (-16.0, -20.0, -14.0), (-13.0, 1.0, -12.0),
            "Extiende la muñeca hacia el meñique", "Extensor cubital del carpo"),
}
for _id, (_nom, _ancla, _via, _acc, _cop) in _MUN.items():
    (_x, _a), _n = _polar_radio(RC_MUN, ANG_MUN[_id])
    MUSCULOS.append(_musc(
        _id, _nom, "G3", "P3", (_x, Y_MUN, _a), (0, -1, 0), _n, Y_GUIA_MUN,
        [("G3", add(W_G3, _via))],                      # paso junto a la muñeca, sobre el radio distal
        ("G5", _ancla, (0.0, -1.0, 0.0)), _acc, _cop))


# ------------------------------------------------------------------ articulaciones
# Giro positivo según la regla de la mano derecha alrededor del eje indicado (coordenadas SW).
ARTICULACIONES = [
    {"id": "hombro_abduccion", "nombre": "Hombro: separar del cuerpo", "hijo": "G1", "eje": (0, 0, 1), "rango": (-20, 100)},
    {"id": "hombro_flexion", "nombre": "Hombro: al frente / atrás", "hijo": "G1", "eje": (1, 0, 0), "rango": (-40, 150)},
    {"id": "hombro_rotacion", "nombre": "Hombro: rotación interna / externa", "hijo": "G1", "eje": (0, 1, 0), "rango": (-60, 80)},
    {"id": "codo_flexion", "nombre": "Codo: doblar", "hijo": "G2", "eje": (1, 0, 0), "rango": (0, 130)},
    {"id": "antebrazo_pronacion", "nombre": "Antebrazo: girar la palma", "hijo": "G3", "eje": mul(W(U_PRONO), -1.0), "rango": (0, 140)},
    {"id": "muneca_flexion", "nombre": "Muñeca: flexión / extensión", "hijo": "G4", "eje": (1, 0, 0), "rango": (-70, 80)},
    {"id": "muneca_desviacion", "nombre": "Muñeca: desviación radial / cubital", "hijo": "G5", "eje": (0, 0, 1), "rango": (-30, 20)},
]
GRUPOS = {"G0": ("hombro", None), "G1": ("brazo", "G0"), "G2": ("cubito", "G1"), "G3": ("radio", "G2"),
          "G4": ("cruceta", "G3"), "G5": ("mano", "G4")}
ORIGEN_EN_PADRE = {"G0": (0, 0, 0), "G1": (0, 0, 0), "G2": E_G1, "G3": P1, "G4": W_G3, "G5": (0, 0, 0)}
POSE_REF = {a["id"]: 0.0 for a in ARTICULACIONES}
POSE_FOTO = dict(POSE_REF, hombro_abduccion=12.0, hombro_flexion=18.0, codo_flexion=55.0,
                 antebrazo_pronacion=20.0, muneca_flexion=-10.0)


def cinematica(q):
    """Transformación (R, t) de cada grupo en el mundo (coordenadas SW, mm) para la pose q (grados)."""
    r = lambda eje, id_: rot_eje(unit(eje), math.radians(q.get(id_, 0.0)))
    T = {"G0": (IDENT, (0.0, 0.0, 0.0))}
    R1 = mmul(mmul(r((0, 0, 1), "hombro_abduccion"), r((1, 0, 0), "hombro_flexion")), r((0, 1, 0), "hombro_rotacion"))
    T["G1"] = (R1, (0.0, 0.0, 0.0))
    R2 = mmul(R1, r((1, 0, 0), "codo_flexion"))
    T["G2"] = (R2, mvec(R1, W(E_G1)))
    R3 = mmul(R2, r(mul(W(U_PRONO), -1.0), "antebrazo_pronacion"))
    t3 = add(T["G2"][1], mvec(R2, W(P1)))
    T["G3"] = (R3, t3)
    R4 = mmul(R3, r((1, 0, 0), "muneca_flexion"))
    t4 = add(t3, mvec(R3, W(W_G3)))
    T["G4"] = (R4, t4)
    T["G5"] = (mmul(R4, r((0, 0, 1), "muneca_desviacion")), t4)
    return T


# ------------------------------------------------------------------ comprobación de holguras
def capsulas():
    """Volúmenes simplificados (cápsulas) por grupo, en coordenadas anatómicas del grupo."""
    c = {g: [] for g in GRUPOS}
    c["G1"] += [("humero", (X_DIAF, -12, 0), (X_DIAF, -250, 0), 12.0),
                ("columna_medial", (-16, -272, -2.5), (-22, -292, -2.5), 5.5),
                ("columna_lateral", (24, -262, -2.5), (26, -272, -2.5), 5.5),
                ("fosa_radial", (24, -274, -5), (30, -292, -5), 3.0)]
    for b in range(130, 290, 15):
        cy, ca = 16 * math.sin(math.radians(b)), 16 * math.cos(math.radians(b))
        c["G2"].append((f"gancho{b}", (-4.0, cy, ca), (4.0, cy, ca), 3.5))
    c["G2"] += [("cubito", UT, P2, 6.5), ("cabeza_cubito", P2, P2, 7.5),
                ("anular", add(P1, mul(U_PRONO, -2.0)), add(P1, mul(U_PRONO, 2.0)), 12.2)]
    c["G3"] += [("tambor", eje_radio(16), eje_radio(40), 10.5), ("cuello", eje_radio(-3), eje_radio(50), 6.5),
                ("radio1", R0, R1, 6.8), ("radio2", R1, R2, 7.5),
                ("radio_distal", add(W_G3, (6, 42, 0)), add(W_G3, (6, 24, 0)), 12.0),
                ("orejas", add(W_G3, (-17.5, 6, 0)), add(W_G3, (17.5, 6, 0)), 8.0)]
    for m in MUSCULOS:
        p = PACK[m["pack"]]
        fin = add(m["O"], mul(m["d"], p["Lmax"]))
        c[m["grupo"]].append((m["id"], add(m["O"], mul(m["d"], p["r_disco"] * 0.5)), fin, p["r_disco"]))
        c[m["grupo"]].append((m["id"] + "_tendon", fin, m["guia"], 4.6))
    return c


def _seg_seg(p1, q1, p2, q2):
    d1, d2, r = sub(q1, p1), sub(q2, p2), sub(p1, p2)
    a, e, f = dot(d1, d1), dot(d2, d2), dot(d2, r)
    if a < 1e-12 and e < 1e-12:
        return norm(r)
    if a < 1e-12:
        s, t = 0.0, max(0.0, min(1.0, f / e))
    else:
        cc = dot(d1, r)
        if e < 1e-12:
            t, s = 0.0, max(0.0, min(1.0, -cc / a))
        else:
            b = dot(d1, d2)
            den = a * e - b * b
            s = max(0.0, min(1.0, (b * f - cc * e) / den)) if den > 1e-12 else 0.0
            t = (b * s + f) / e
            if t < 0:
                t, s = 0.0, max(0.0, min(1.0, -cc / a))
            elif t > 1:
                t, s = 1.0, max(0.0, min(1.0, (b - cc) / a))
    return norm(sub(add(p1, mul(d1, s)), add(p2, mul(d2, t))))


def holgura(q, grupos_a, grupos_b, caps=None):
    """Holgura mínima (mm) entre las cápsulas de dos conjuntos de grupos en la pose q."""
    caps = caps or capsulas()
    T = cinematica(q)
    def mundo(g, p):
        R, t = T[g]
        return add(mvec(R, W(p)), t)
    mejor = (1e9, None)
    for ga in grupos_a:
        for na, a1, b1, r1 in caps[ga]:
            A1, B1 = mundo(ga, a1), mundo(ga, b1)
            for gb in grupos_b:
                for nb, a2, b2, r2 in caps[gb]:
                    if "anular" in (na, nb) and (na in ("cuello", "tambor") or nb in ("cuello", "tambor")):
                        continue        # el rodamiento anular abraza la cabeza del radio a propósito
                    d = _seg_seg(A1, B1, mundo(gb, a2), mundo(gb, b2)) - r1 - r2
                    if d < mejor[0]:
                        mejor = (d, (na, nb))
    return mejor


if __name__ == "__main__":
    print("P1 (G2):", [round(v, 3) for v in P1], " eje:", [round(v, 4) for v in U_PRONO])
    print("W en G3:", [round(v, 3) for v in W_G3], " R0,R1,R2 en G3:", [[round(v, 2) for v in p] for p in (R0, R1, R2)])
    for m in MUSCULOS:
        print(m["id"], m["nombre"], m["grupo"], m["pack"], "O", [round(v, 1) for v in m["O"]], "T", m["T"])
    caps = capsulas()
    print("\nPronación (cúbito contra radio y sus músculos):")
    for g in range(0, 181, 15):
        h = holgura(dict(POSE_REF, antebrazo_pronacion=g), ["G2"], ["G3"], caps)
        print(f"  {g:3d}°  {h[0]:6.1f} mm  {h[1]}")
    print("\nFlexión del codo (brazo contra antebrazo), con pronación 0 / 75 / 150:")
    for g in range(0, 151, 15):
        fila = []
        for pr in (0, 75, 150):
            h = holgura(dict(POSE_REF, codo_flexion=g, antebrazo_pronacion=pr), ["G1"], ["G2", "G3"], caps)
            fila.append(f"{h[0]:6.1f} {h[1]}")
        print(f"  {g:3d}°  " + " | ".join(fila))
    print("\nMuñeca del grupo G3 contra G1 en referencia:", holgura(POSE_REF, ["G1"], ["G3"], caps))
    print("Paquetes del brazo entre sí:")
    g1 = [c for c in caps["G1"] if c[0].startswith("M") and not c[0].endswith("tendon")]
    for i in range(len(g1)):
        for j in range(i + 1, len(g1)):
            d = _seg_seg(g1[i][1], g1[i][2], g1[j][1], g1[j][2]) - g1[i][3] - g1[j][3]
            if d < 3:
                print("  ", g1[i][0], g1[j][0], round(d, 1))
    g3 = [c for c in caps["G3"] if c[0].startswith("M") and not c[0].endswith("tendon")]
    print("Paquetes de la muñeca entre sí y contra el radio:")
    for i in range(len(g3)):
        for j in range(i + 1, len(g3)):
            d = _seg_seg(g3[i][1], g3[i][2], g3[j][1], g3[j][2]) - g3[i][3] - g3[j][3]
            if d < 3:
                print("  ", g3[i][0], g3[j][0], round(d, 1))
