"""Optimizador de inserciones del hombro: primer experimento de diseño computacional.

Idea (la misma que usa Leap 71 con sus motores): no dibujamos dónde se ancla cada tendón;
damos las reglas (física del peso, fuerza de cada músculo, dónde puede ir un anclaje,
holguras, recorrido del tendón) y dejamos que un buscador pruebe miles de combinaciones.

Qué se optimiza: el punto de anclaje en el húmero (grupo G1) de los seis músculos del
hombro M01..M06 y, con --guias, también la salida del tendón en el hombro (G0).

Qué se mide en cada postura de una rejilla (hombro + codo):
  * par sin equilibrar (N·m): lo que el peso pide y los músculos no pueden dar;
  * esfuerzo: suma de activaciones al cuadrado (0 = nada, 1 = músculo al 100 %);
  * saturación: activaciones por encima de 1 (el músculo no llega).
Y en todo el conjunto:
  * holgura: el tendón no debe atravesar la cabeza ni la diáfisis del húmero;
  * recorrido: cuánto cambia el largo del tendón (alarga la cuerda del actuador v1).

Usa exactamente el mismo cálculo que el simulador (software/simulador/index.html: bioGravity,
bioArms, nnls, bioHold): misma cinemática (flexión → separación → rotación), mismas masas,
mano de 500 g y fuerzas máximas P4 = 160 N, P3 = 120 N. --validar lo comprueba contra
valores sacados del simulador con __sim.bioFrames y __sim.bioLoad.

Uso:
  python cad/optimizador/inserciones.py --validar
  python cad/optimizador/inserciones.py --optimizar [--guias] [--semillas 8] [--evals 4000]

Solo biblioteca estándar, como param.py. Todo en mm salvo los pares (N·m).
"""
import argparse
import json
import math
import os
import random
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
MODELO = os.path.join(RAIZ, "software", "simulador", "modelo3d", "modelo.json")
SALIDA = os.path.join(AQUI, "resultados")

# ---------------------------------------------------------------- constantes del simulador
G_ACC, HAND_KG, LAMBDA = 9.81, 0.5, 0.01
F_MAX = {"P4": 160.0, "P3": 120.0}
BIO_MAP = ["hombro_flexion", "hombro_abduccion", "hombro_rotacion", "codo_flexion",
           "antebrazo_pronacion", "muneca_flexion", "muneca_desviacion"]
PARENT = {"G1": 2, "G2": 3, "G3": 4, "G4": 5, "G5": 6}     # última articulación que mueve cada grupo
# Masa y centro de masas de cada grupo (kg; mm en el grupo), tal como los calcula el simulador a partir
# de las mallas (__sim.bioFrames(...).masas). Si se regenera el CAD hay que volver a copiarlos.
MASAS = {
    "G1": (0.452087, (7.8876, -128.5415, -1.1695)),
    "G2": (0.050793, (6.4808, -77.6659, 4.6603)),
    "G3": (0.199103, (21.9160, -133.0871, 0.6265)),
    "G4": (0.021207, (0.0, 0.0, 0.0)),
    "G5": (0.043836, (0.0, -20.9560, 0.0)),
}
MANO_G5 = (0.0, -62.0, 0.0)            # centro de la palma (donde el simulador pone los 500 g de la mano)
JO3 = (0.0, -300.0, 0.0)               # articulaciones en la postura cero (mm, mundo = G0)
JO4 = (21.264176336281310, -313.98064961065514, 0.0)
JO5 = (27.0, -556.0, 0.0)
AX4 = (0.052558833122763673, 0.9986178293325098, 0.0)      # eje de pronosupinación en G2

# ---------------------------------------------------------------- reglas del diseño
X_DIAF = 9.0                 # eje de la diáfisis del húmero (SW: x = 9, z = 0)
R_HUMERO = 12.0              # radio de la diáfisis
R_CABEZA = 22.0              # cabeza humeral, esfera en el origen
TENDON_R = 1.5
RHO = (11.0, 30.0)           # distancia del anclaje al eje del húmero: sobre el hueso o en un saliente de hasta 18 mm
Y_ANCLA = (-180.0, -5.0)     # a lo largo del húmero (la tuberosidad deltoidea real está en -125)
D_GUIA = 30.0                # con --guias: cuánto puede moverse la salida del tendón en el hombro (y, z)
EXC_MAX = 1.25               # recorrido permitido respecto al diseño v0 (cuerda más larga = actuador más largo)
HOMBRO = ["M01", "M02", "M03", "M04", "M05", "M06"]

# Pesos del coste. El par sin equilibrar manda: es el fallo que queremos quitar.
W_RESID, W_ESF, W_SAT, W_HOLG, W_EXC = 20.0, 1.0, 20.0, 0.05, 0.05


# ---------------------------------------------------------------- álgebra mínima
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return math.sqrt(dot(a, a))
def mv(R, v): return tuple(R[i][0] * v[0] + R[i][1] * v[1] + R[i][2] * v[2] for i in range(3))
def mtv(R, v): return tuple(R[0][i] * v[0] + R[1][i] * v[1] + R[2][i] * v[2] for i in range(3))
def mm(A, B): return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def rot(u, ang):
    x, y, z = mul(u, 1.0 / norm(u))
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    return [[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C]]


X, Y, Z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
I3 = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]


# ---------------------------------------------------------------- cinemática y física (copia del simulador)
def cinematica(qdeg):
    """Grupos {id: (R, t)} y articulaciones (jo, ja) en el mundo, en mm, para q en grados (orden BIO_MAP)."""
    a = [math.radians(v) for v in qdeg]
    R0 = rot(X, a[0])
    R01 = mm(R0, rot(Z, a[1]))
    R1 = mm(R01, rot(Y, a[2]))
    R2 = mm(R1, rot(X, a[3]))
    t2 = mv(R1, JO3)
    t3 = add(t2, mv(R2, sub(JO4, JO3)))
    R3 = mm(R2, rot(AX4, a[4]))
    t4 = add(t3, mv(R3, sub(JO5, JO4)))
    R4 = mm(R3, rot(X, a[5]))
    R5 = mm(R4, rot(Z, a[6]))
    O = (0.0, 0.0, 0.0)
    T = {"G0": (I3, O), "G1": (R1, O), "G2": (R2, t2), "G3": (R3, t3), "G4": (R4, t4), "G5": (R5, t4)}
    jo = [O, O, O, t2, t3, t4, t4]
    ja = [X, mv(R0, Z), mv(R1, Y), mv(R1, X), mv(R2, AX4), mv(R3, X), mv(R4, Z)]
    return T, jo, ja


def mundo(T, grupo, p):
    R, t = T[grupo]
    return add(mv(R, p), t)


def gravedad(T, jo, ja):
    tau = [0.0] * 7

    def suma(p, kg, last):
        fy = -kg * G_ACC
        for k in range(last + 1):
            rx, rz = (p[0] - jo[k][0]) / 1000.0, (p[2] - jo[k][2]) / 1000.0
            tau[k] += ja[k][0] * (-rz * fy) + ja[k][2] * (rx * fy)
    for g, (kg, c) in MASAS.items():
        suma(mundo(T, g, c), kg, PARENT[g])
    suma(mundo(T, "G5", MANO_G5), HAND_KG, 6)
    return tau


def topes(qdeg, tau, lim):
    tol = math.degrees(0.01)
    return [0.0 if (q <= lo + tol and t < 0) or (q >= hi - tol and t > 0) else t
            for q, t, (lo, hi) in zip(qdeg, tau, lim)]


def brazos(T, jo, ja, ruta):
    """dL/dq (m/rad) de un tendón con ruta [(grupo, p_mm), ...]: exacto tramo a tramo, como bioArms."""
    r = [0.0] * 7
    gA, pA = ruta[0]
    ia, A = (-1 if gA == "G0" else PARENT[gA]), mundo(T, gA, pA)
    for gB, pB in ruta[1:]:
        ib, B = (-1 if gB == "G0" else PARENT[gB]), mundo(T, gB, pB)
        u = sub(B, A)
        u = mul(u, 1.0 / norm(u))
        for k in range(max(ia, ib) + 1):
            v = (0.0, 0.0, 0.0)
            if ib >= k: v = add(v, cross(ja[k], sub(B, jo[k])))
            if ia >= k: v = sub(v, cross(ja[k], sub(A, jo[k])))
            r[k] += dot(u, v) / 1000.0
        A, ia = B, ib
    return r


def largo(T, ruta):
    P = [mundo(T, g, p) for g, p in ruta]
    return sum(norm(sub(P[i + 1], P[i])) for i in range(len(P) - 1))


def resolver(M, b):
    n = len(b)
    A = [list(M[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda i: abs(A[i][c]))
        A[c], A[p] = A[p], A[c]
        if abs(A[c][c]) < 1e-15:
            continue
        for i in range(c + 1, n):
            f = A[i][c] / A[c][c]
            for j in range(c, n + 1):
                A[i][j] -= f * A[c][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = A[i][n] - sum(A[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / A[i][i] if abs(A[i][i]) > 1e-15 else 0.0
    return x


def nnls(H, b):
    """Lawson y Hanson sobre H x = b con x >= 0 (copia de nnls del simulador)."""
    n = len(b)
    x, inP = [0.0] * n, [False] * n

    def grad():
        return [b[a] - sum(H[a][c] * x[c] for c in range(n)) for a in range(n)]
    w = grad()
    for _ in range(3 * n):
        jm, wm = -1, 1e-9
        for i in range(n):
            if not inP[i] and w[i] > wm:
                wm, jm = w[i], i
        if jm < 0:
            break
        inP[jm] = True
        for _ in range(3 * n):
            idx = [i for i in range(n) if inP[i]]
            z = resolver([[H[a][c] for c in idx] for a in idx], [b[a] for a in idx])
            if all(v > 1e-12 for v in z):
                x = [0.0] * n
                for a, v in zip(idx, z):
                    x[a] = v
                break
            al = 1.0
            for a, v in zip(idx, z):
                if v <= 1e-12:
                    al = min(al, x[a] / (x[a] - v))
            for a, v in zip(idx, z):
                x[a] += al * (v - x[a])
                if x[a] <= 1e-12:
                    x[a], inP[a] = 0.0, False
        w = grad()
    return x


def sostener(tau, A, juntas):
    """Activaciones x >= 0 con sum_j A_j[k] x_j ≈ tau_k en las articulaciones dadas; y el par sin equilibrar."""
    n = len(A)
    H = [[(LAMBDA if i == j else 0.0) + sum(A[i][k] * A[j][k] for k in juntas) for j in range(n)] for i in range(n)]
    b = [sum(A[i][k] * tau[k] for k in juntas) for i in range(n)]
    x = nnls(H, b)
    res = max(abs(sum(A[j][k] * x[j] for j in range(n)) - tau[k]) for k in juntas)
    return x, res


# ---------------------------------------------------------------- modelo y posturas
def cargar():
    with open(MODELO, encoding="utf-8") as f:
        m = json.load(f)
    art = {a["id"]: a for a in m["articulaciones"]}
    lim = [tuple(art[i]["rango"]) for i in BIO_MAP]
    mus = {u["id"]: {"pack": u["paquete"], "nombre": u["nombre"],
                     "ruta": [(r["grupo"], tuple(r["p"])) for r in u["ruta"]]} for u in m["musculos"]}
    return mus, lim


def rejilla():
    """Hombro al frente 0–150°, separado 0–90°, rotado ±30°, codo recto y a 90°: 144 posturas."""
    return [[f, a, r, e, 0, 0, 0] for f in range(0, 151, 30) for a in range(0, 91, 30)
            for r in (-30, 0, 30) for e in (0, 90)]


class Problema:
    """Precalcula lo que no cambia al mover los anclajes del hombro (marcos y par del peso)."""

    def __init__(self, mus, lim, posturas):
        self.mus, self.post = mus, posturas
        self.datos = []
        for q in posturas:
            T, jo, ja = cinematica(q)
            tau = topes(q, gravedad(T, jo, ja), lim)
            self.datos.append((T, jo, ja, tau))

    def evaluar(self, rutas, base=None, detalle=False):
        """base = (recorridos, holguras) del v0 por músculo: el coste castiga pasar de esos valores."""
        n = len(HOMBRO)
        resid, esf, sat, Lmin, Lmax, peor = [], [], [], [1e9] * n, [-1e9] * n, (0.0, None)
        acts = []
        for (T, jo, ja, tau), q in zip(self.datos, self.post):
            A = []
            for j, mid in enumerate(HOMBRO):
                f = F_MAX[self.mus[mid]["pack"]]
                A.append([v * f for v in brazos(T, jo, ja, rutas[mid])])
                L = largo(T, rutas[mid])
                Lmin[j], Lmax[j] = min(Lmin[j], L), max(Lmax[j], L)
            x, res = sostener(tau, A, (0, 1, 2))
            resid.append(res)
            esf.append(sum(v * v for v in x))
            sat.append(sum(max(0.0, v - 1.0) ** 2 for v in x))
            acts.append(x)
            if res > peor[0]:
                peor = (res, q)
        exc = [Lmax[j] - Lmin[j] for j in range(n)]
        holg = holgura(rutas)
        pen_exc = pen_holg = 0.0
        if base:
            pen_exc = sum(max(0.0, e - EXC_MAX * b) ** 2 for e, b in zip(exc, base[0]))
            pen_holg = sum(max(0.0, h - b) for h, b in zip(holg, base[1]))
        N = len(resid)
        J = (W_RESID * sum(r * r for r in resid) / N + W_ESF * sum(esf) / N + W_SAT * sum(sat) / N
             + W_HOLG * pen_holg + W_EXC * pen_exc)
        if not detalle:
            return J
        amax = max(max(x) for x in acts)
        return {"coste": round(J, 4),
                "par_sin_equilibrar_max_Nm": round(max(resid), 3),
                "par_sin_equilibrar_medio_Nm": round(sum(resid) / N, 3),
                "posturas_con_mas_de_0_1_Nm": sum(1 for r in resid if r > 0.1),
                "peor_postura": peor[1],
                "esfuerzo_medio": round(sum(esf) / N, 3),
                "activacion_max": round(amax, 3),
                "activacion_media_por_musculo": {m: round(sum(x[j] for x in acts) / N, 3) for j, m in enumerate(HOMBRO)},
                "recorrido_mm": {m: round(e, 1) for m, e in zip(HOMBRO, exc)},
                "invasion_holgura_mm2": {m: round(h, 0) for m, h in zip(HOMBRO, holg)},
                "posturas": N}


# ---------------------------------------------------------------- holgura (en el marco del húmero, G1)
def _seg_seg(p1, q1, p2, q2):
    d1, d2, r = sub(q1, p1), sub(q2, p2), sub(p1, p2)
    a, e, f = dot(d1, d1), dot(d2, d2), dot(d2, r)
    c, b = dot(d1, r), dot(d1, d2)
    den = a * e - b * b
    s = max(0.0, min(1.0, (b * f - c * e) / den)) if den > 1e-12 else 0.0
    t = (b * s + f) / e
    if t < 0:
        t, s = 0.0, max(0.0, min(1.0, -c / a))
    elif t > 1:
        t, s = 1.0, max(0.0, min(1.0, (b - c) / a))
    return norm(sub(add(p1, mul(d1, s)), add(p2, mul(d2, t))))


def _seg_punto(p, q, c):
    d = sub(q, p)
    s = max(0.0, min(1.0, dot(sub(c, p), d) / dot(d, d)))
    return norm(sub(add(p, mul(d, s)), c))


_HOLG_POST = [[f, a, r, 0, 0, 0, 0] for f in (-40, 0, 60, 120, 150) for a in (-20, 0, 45, 100) for r in (-60, 0, 80)]
_HOLG_T = [cinematica(q)[0] for q in _HOLG_POST]


def holgura(rutas):
    """Por músculo: suma de (mm que el tendón invade la cabeza o la diáfisis)² en posturas de todo el rango
    del hombro. Se ignoran los últimos 8 mm antes del anclaje, que por definición toca el hueso.
    Ojo: el v0 ya invade mucho, porque el modelo lleva el tendón en línea recta y no lo hace rodear la
    cabeza (en el cuerpo el deltoides se apoya sobre ella). Por eso el coste solo castiga empeorar al v0."""
    out = []
    eje0, eje1 = (X_DIAF, -30.0, 0.0), (X_DIAF, -250.0, 0.0)
    for mid in HOMBRO:
        tot = 0.0
        (g0, pg), (g1, pa) = rutas[mid][0], rutas[mid][-1]
        for T in _HOLG_T:
            R1 = T["G1"][0]
            G = mtv(R1, pg)                           # la salida del tendón vista desde el húmero
            u = sub(pa, G)
            L = norm(u)
            if L <= 9.0:                              # tendón casi nulo: el anclaje está pegado a la salida
                continue
            B = add(G, mul(u, (L - 8.0) / L))
            d_cab = _seg_punto(G, B, (0.0, 0.0, 0.0)) - (R_CABEZA + TENDON_R)
            d_dia = _seg_seg(G, B, eje0, eje1) - (R_HUMERO + TENDON_R)
            tot += min(0.0, d_cab) ** 2 + min(0.0, d_dia) ** 2
        out.append(tot)
    return out


# ---------------------------------------------------------------- variables de diseño
def a_cilindricas(p):
    dx, dz = p[0] - X_DIAF, p[2]
    return math.atan2(dz, dx), math.hypot(dx, dz), p[1]


def de_cilindricas(th, rho, y):
    return (X_DIAF + rho * math.cos(th), y, rho * math.sin(th))


class Diseno:
    """Vector de números en [0, 1] (salvo el ángulo, que da la vuelta) <-> rutas de los músculos del hombro."""

    def __init__(self, mus, guias):
        self.mus, self.guias = mus, guias
        self.base = {m: mus[m]["ruta"] for m in HOMBRO}

    def inicial(self):
        v = []
        for m in HOMBRO:
            th, rho, y = a_cilindricas(self.base[m][-1][1])
            v += [th / (2 * math.pi), (rho - RHO[0]) / (RHO[1] - RHO[0]), (y - Y_ANCLA[0]) / (Y_ANCLA[1] - Y_ANCLA[0])]
            if self.guias:
                v += [0.5, 0.5]
        return [min(1.0, max(0.0, x)) if (i % self.paso()) else x for i, x in enumerate(v)]

    def paso(self):
        return 5 if self.guias else 3

    def rutas(self, v):
        out, k = {}, 0
        for m in HOMBRO:
            th = 2 * math.pi * v[k]
            rho = RHO[0] + (RHO[1] - RHO[0]) * min(1.0, max(0.0, v[k + 1]))
            y = Y_ANCLA[0] + (Y_ANCLA[1] - Y_ANCLA[0]) * min(1.0, max(0.0, v[k + 2]))
            (g0, pg), (g1, _) = self.base[m][0], self.base[m][-1]
            if self.guias:
                dy = D_GUIA * (2 * min(1.0, max(0.0, v[k + 3])) - 1)
                dz = D_GUIA * (2 * min(1.0, max(0.0, v[k + 4])) - 1)
                pg = (pg[0], pg[1] + dy, pg[2] + dz)
            out[m] = [(g0, pg), (g1, de_cilindricas(th, rho, y))]
            k += self.paso()
        return out


# ---------------------------------------------------------------- buscador: Nelder–Mead con reinicios
def nelder_mead(f, x0, paso=0.15, evals=3000, tol=1e-6):
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (paso if j == i else 0.0) for j in range(n)] for i in range(n)]
    val = [f(p) for p in pts]
    usados = n + 1
    while usados < evals:
        orden = sorted(range(n + 1), key=lambda i: val[i])
        pts, val = [pts[i] for i in orden], [val[i] for i in orden]
        if val[-1] - val[0] < tol:
            break
        c = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        xr = [c[j] + (c[j] - pts[-1][j]) for j in range(n)]
        fr = f(xr); usados += 1
        if fr < val[0]:
            xe = [c[j] + 2 * (c[j] - pts[-1][j]) for j in range(n)]
            fe = f(xe); usados += 1
            pts[-1], val[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < val[-2]:
            pts[-1], val[-1] = xr, fr
        else:
            xc = [c[j] + 0.5 * (pts[-1][j] - c[j]) for j in range(n)]
            fc = f(xc); usados += 1
            if fc < val[-1]:
                pts[-1], val[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    pts[i] = [pts[0][j] + 0.5 * (pts[i][j] - pts[0][j]) for j in range(n)]
                    val[i] = f(pts[i]); usados += 1
    i = min(range(n + 1), key=lambda i: val[i])
    return pts[i], val[i], usados


def rejilla_busqueda():
    """48 posturas repartidas por el mismo espacio que rejilla(): para buscar rápido (3 veces menos cálculo).
    El resultado final se mide siempre con la rejilla completa."""
    return [[f, a, r, e, 0, 0, 0] for f in (0, 45, 90, 135) for a in (0, 45, 90) for r in (-30, 30) for e in (0, 90)]


def optimizar(args):
    mus, lim = cargar()
    prob = Problema(mus, lim, rejilla())
    busca = Problema(mus, lim, rejilla_busqueda())
    dis = Diseno(mus, args.guias)
    base = {m: mus[m]["ruta"] for m in HOMBRO}
    ref = prob.evaluar(base, detalle=True)
    lb = ([ref["recorrido_mm"][m] for m in HOMBRO], holgura(base))
    ref["coste"] = round(prob.evaluar(base, lb), 4)
    f = lambda v: busca.evaluar(dis.rutas(v), lb)
    print("Diseño v0:", json.dumps(ref, ensure_ascii=False))
    rnd = random.Random(args.semilla)
    mejor, t0 = (None, 1e18), time.time()
    for s in range(args.semillas):
        x0 = dis.inicial() if s == 0 else [rnd.random() for _ in dis.inicial()]
        x = x0
        for vuelta in range(args.vueltas):                  # reiniciar el símplex alrededor del mejor punto
            x, J, k = nelder_mead(f, x, paso=0.15 / (vuelta + 1), evals=args.evals)
        tag = "v0" if s == 0 else f"azar {s}"
        print(f"  semilla {s:2d} ({tag:7s}): coste {J:8.4f}   [{time.time() - t0:5.0f} s]", flush=True)
        if J < mejor[1]:
            mejor = (x, J)
    rutas = dis.rutas(mejor[0])
    res = prob.evaluar(rutas, lb, detalle=True)
    print("Mejor:", json.dumps(res, ensure_ascii=False))
    os.makedirs(SALIDA, exist_ok=True)
    nombre = os.path.join(SALIDA, "hombro_guias.json" if args.guias else "hombro_anclajes.json")
    anclas = {}
    for m in HOMBRO:
        g, p = rutas[m][-1]
        th, rho, y = a_cilindricas(p)
        anclas[m] = {"nombre": mus[m]["nombre"], "v0": [round(c, 1) for c in base[m][-1][1]],
                     "nuevo": [round(c, 1) for c in p], "guia_v0": [round(c, 1) for c in base[m][0][1]],
                     "guia_nueva": [round(c, 1) for c in rutas[m][0][1]],
                     "angulo_grados": round(math.degrees(th) % 360, 0), "distancia_al_eje_mm": round(rho, 1)}
    with open(nombre, "w", encoding="utf-8") as fh:
        json.dump({"reglas": {"rho_mm": RHO, "y_mm": Y_ANCLA, "guias": args.guias, "d_guia_mm": D_GUIA if args.guias else 0,
                              "recorrido_max": EXC_MAX, "posturas": "rejilla() de inserciones.py",
                              "coordenadas": "SolidWorks, mm, en el grupo (G1 húmero, G0 hombro)"},
                   "v0": ref, "optimo": res, "anclajes": anclas}, fh, ensure_ascii=False, indent=1)
    print("Guardado en", os.path.relpath(nombre, RAIZ))


# ---------------------------------------------------------------- validación contra el simulador
# Valores de __sim.bioFrames(q).tau y __sim.bioLoad(q) (brazos r en mm/rad y activaciones a) del simulador.
VAL_TAU = {
    (90, 0, 0, 0, 0, 0, 0): [-5.0265, 0, -0.2722, 0, 0, -0.3131, 0],
    (30, 30, 0, 90, 0, 0, 0): [-3.0057, -1.4911, 0.7573, -1.5453, 0, -0.2348, -0.1356],
    (120, 30, -30, 90, 0, 0, 0): [-0.8548, 1.2918, -1.5103, 0.889, 0.0766, 0.1356, 0.2034],
    (0, 60, 30, 0, 0, 0, 0): [-0.1375, -4.4706, 0.1191, 0.893, 0.0749, 0.1356, -0.2348],
}
VAL_ARM = {
    (90, 0, 0, 0, 0, 0, 0): {"M01": [-74.9, -14.4, -7.2], "M03": [-56.4, -30.2, -10.4], "M04": [39, 10, -1.5],
                             "M06": [23, 11.4, -5], "M07": [0, 0, 0, -13.6, 2.5]},
    (120, 60, -30, 90, 0, 0, 0): {"M01": [-13.4, 64.6, -7.1], "M05": [18.1, -12.9, -16.1], "M10": [0, 0, 0, -7.2, -7.9]},
}
VAL_ACT = {   # activaciones del simulador con los 15 músculos; residuo máximo en las 7 articulaciones
    (45, 30, 20, 60, 0, 0, 0): ({"M01": 0.41, "M05": 0.28, "M07": 0.193, "M08": 0.26, "M10": 0.159, "M12": 0.145}, 0.5697),
    (120, 60, -30, 90, 0, 0, 0): ({"M01": 0.257, "M03": 0.141, "M04": 0.101, "M05": 0.668, "M09": 0.193}, 0.0028),
}


def validar():
    mus, lim = cargar()
    ok = True
    for q, ref in VAL_TAU.items():
        T, jo, ja = cinematica(q)
        tau = topes(q, gravedad(T, jo, ja), lim)
        e = max(abs(a - b) for a, b in zip(tau, ref))
        print(f"par del peso {q}: error máx {e:.4f} N·m")
        ok &= e < 0.002
    for q, refs in VAL_ARM.items():
        T, jo, ja = cinematica(q)
        for mid, ref in refs.items():
            r = brazos(T, jo, ja, mus[mid]["ruta"])
            e = max(abs(r[k] * 1000 - v) for k, v in enumerate(ref))
            print(f"brazo de palanca {mid} {q}: error máx {e:.2f} mm/rad")
            ok &= e < 0.06
    ids = sorted(mus)
    for q, (ref, rref) in VAL_ACT.items():
        T, jo, ja = cinematica(q)
        tau = topes(q, gravedad(T, jo, ja), lim)
        A = [[v * F_MAX[mus[m]["pack"]] for v in brazos(T, jo, ja, mus[m]["ruta"])] for m in ids]
        x, res = sostener(tau, A, range(7))
        e = max(abs(x[ids.index(m)] - v) for m, v in ref.items())
        print(f"activaciones {q}: error máx {e:.4f}; par sin equilibrar {res:.4f} (simulador {rref})")
        ok &= e < 0.002 and abs(res - rref) < 0.002
    print("VALIDACIÓN", "CORRECTA" if ok else "FALLIDA")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--validar", action="store_true")
    ap.add_argument("--optimizar", action="store_true")
    ap.add_argument("--guias", action="store_true", help="mover también la salida del tendón en el hombro")
    ap.add_argument("--semillas", type=int, default=6)
    ap.add_argument("--vueltas", type=int, default=3)
    ap.add_argument("--evals", type=int, default=1500)
    ap.add_argument("--semilla", type=int, default=71)
    a = ap.parse_args()
    if a.validar or not a.optimizar:
        validar()
    if a.optimizar:
        optimizar(a)
