"""Utilidades sobre swlib para generar el brazo biomimético por código.

Convenio anatómico usado en TODO el generador (brazo derecho, igual que el simulador web):
    x = lateral (hacia fuera del cuerpo)   -> X de SolidWorks
    y = arriba                              -> Y de SolidWorks
    a = anterior (hacia delante)            -> -Z de SolidWorks  (la persona mira hacia -Z)
Las piezas se describen con puntos (x, y, a) en mm. La conversión a SolidWorks se hace aquí.
"""
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "solidworks-mcp"))

import pythoncom  # noqa: E402
import swlib as s  # noqa: E402

MM = 0.001
IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


# ------------------------------------------------------------------ vectores
def v_sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def v_add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def v_mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def v_dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def v_cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def v_norm(a): return math.sqrt(v_dot(a, a))
def v_unit(a):
    n = v_norm(a)
    return (a[0] / n, a[1] / n, a[2] / n)


def mundo(p):
    """(x, y, a) anatómico -> (X, Y, Z) de SolidWorks."""
    return (p[0], p[1], -p[2])


def m_mul(A, B):
    return tuple(tuple(sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def m_vec(A, v):
    return tuple(sum(A[i][k] * v[k] for k in range(3)) for i in range(3))


def m_cols(cx, cy, cz):
    """Matriz cuyas columnas son las imágenes de los ejes locales X, Y, Z."""
    return ((cx[0], cy[0], cz[0]), (cx[1], cy[1], cz[1]), (cx[2], cy[2], cz[2]))


def rot_eje(u, ang):
    """Matriz de giro alrededor del vector unitario u (regla de la mano derecha), ang en radianes."""
    c, s_, t = math.cos(ang), math.sin(ang), 1 - math.cos(ang)
    x, y, z = u
    return ((t * x * x + c, t * x * y - s_ * z, t * x * z + s_ * y),
            (t * x * y + s_ * z, t * y * y + c, t * y * z - s_ * x),
            (t * x * z - s_ * y, t * y * z + s_ * x, t * z * z + c))


def marco_hacia(direccion, fuera=None):
    """Giro (coordenadas de SolidWorks) que lleva el eje local -Y a `direccion` y el eje local +X
    a `fuera` (se ortogonaliza). Ambos vectores van en coordenadas de SolidWorks."""
    d = v_unit(direccion)
    ly = v_mul(d, -1.0)
    if fuera is None:
        fuera = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 0.0, 1.0)
    f = v_sub(fuera, v_mul(ly, v_dot(fuera, ly)))
    lx = v_unit(f)
    lz = v_cross(lx, ly)
    return m_cols(lx, ly, lz)


# ------------------------------------------------------------------ sesión
def iniciar(cerrar_todo=True):
    pythoncom.CoInitialize()
    sw = s.conectar()
    if cerrar_todo:
        sw.CloseAllDocuments(True)
        ABIERTOS.clear()
    try:
        sw.CommandInProgress = True      # acelera las llamadas a la API desde otro proceso
    except Exception:  # noqa: BLE001
        pass
    try:   # STL binario, en mm
        sw.SetUserPreferenceToggle(s.K.swSTLBinaryFormat, True)
        sw.SetUserPreferenceIntegerValue(s.K.swExportStlUnits, 0)
        sw.SetUserPreferenceToggle(s.K.swSTLDontTranslateToPositive, True)
        sw.SetUserPreferenceIntegerValue(s.K.swSTLQuality, 2)   # personalizada
        sw.SetUserPreferenceDoubleValue(s.K.swSTLDeviation, 0.00012)
        sw.SetUserPreferenceDoubleValue(s.K.swSTLAngleTolerance, math.radians(12))
    except Exception as e:  # noqa: BLE001
        print("aviso: preferencias STL:", e)
    return sw


def _mover(ents, dx, dy):
    out = []
    for e in ents:
        e = dict(e)
        for k in ("x", "x1", "x2", "x3", "cx"):
            if k in e:
                e[k] = e[k] - dx
        for k in ("y", "y1", "y2", "y3", "cy"):
            if k in e:
                e[k] = e[k] - dy
        if "puntos" in e:
            e["puntos"] = [(p[0] - dx, p[1] - dy) for p in e["puntos"]]
        out.append(e)
    return out


COLOR = {
    "hueso": (0.93, 0.90, 0.80),
    "hueso2": (0.86, 0.82, 0.70),
    "acero": (0.62, 0.65, 0.70),
    "aluminio": (0.80, 0.82, 0.85),
    "oscuro": (0.20, 0.22, 0.25),
    "tendon": (0.96, 0.94, 0.86),
    "uS": (0.98, 0.62, 0.55),
    "uM": (0.86, 0.27, 0.24),
    "uL": (0.56, 0.10, 0.13),
    "resorte": (0.20, 0.55, 0.60),
    "guia": (0.95, 0.75, 0.20),
    "ancla": (0.95, 0.55, 0.15),
    "soporte": (0.30, 0.33, 0.38),
    "mano": (0.55, 0.58, 0.62),
    "montura": (0.36, 0.40, 0.46),
}


class Pieza:
    """Pieza nueva descrita en coordenadas anatómicas del grupo.

    origen: punto (x, y, a) del grupo que será el origen de la pieza (por defecto el del grupo).
    Las operaciones reciben coordenadas del grupo; aquí se restan y se pasan a SolidWorks.
    """

    def __init__(self, nombre, carpeta, origen=(0.0, 0.0, 0.0)):
        self.nombre = nombre
        self.ruta = os.path.join(carpeta, nombre + ".SLDPRT")
        self.o = origen
        self.md = s.nuevo("pieza")
        self.planos = {}
        self.n = 0

    # -- planos
    def _pl(self, base, d):
        if abs(d) < 1e-6:
            return base
        k = (base, round(d, 4))
        if k not in self.planos:
            self.planos[k] = s.plano_desfasado(base, d, md=self.md)
        return self.planos[k]

    def _nom(self, f, nombre):
        self.n += 1
        if nombre:
            try:
                s.feature(f, self.md).Name = nombre
                return nombre
            except Exception:  # noqa: BLE001
                pass
        return f

    def _croquis(self, vista, ents, c):
        """vista 'frontal': ents en (x, y), c = a del plano. 'lateral': ents en (a, y), c = x.
        'superior': ents en (x, a), c = y."""
        ox, oy, oa = self.o
        if vista == "frontal":
            ents = _mover(ents, ox, oy); d = -(c - oa)
        elif vista == "lateral":
            ents = _mover(ents, oa, oy); d = c - ox
        elif vista == "superior":
            ents = _mover(ents, ox, oa); d = c - oy
        else:
            raise ValueError(vista)
        return s.croquis(ents, self._pl(vista, d), md=self.md)

    # -- extrusiones
    def ext(self, vista, ents, c0, c1, corte=False, nombre=None):
        """Extruye entre las cotas c0 y c1 del eje perpendicular a la vista
        (frontal: a; lateral: x; superior: y)."""
        lo, hi = min(c0, c1), max(c0, c1)
        base = hi if vista == "frontal" else lo      # frontal: +Z de SW es -a
        sk = self._croquis(vista, ents, base)
        if corte:
            # FeatureCut4(Sd, Flip, Dir, ...): Flip cambia el LADO que se corta; Dir cambia el sentido.
            # Sin Dir el corte va contra la normal del croquis, así que aquí va con Dir=True.
            s._seleccionar_croquis(sk, self.md)
            K = s.K
            f = self.md.FeatureManager.FeatureCut4(
                True, False, True, K.swEndCondBlind, K.swEndCondBlind, (hi - lo) * MM, 0,
                False, False, False, False, 0, 0, False, False, False, False,
                False, True, True, True, True, False, 0, 0, False, False)
            if f is None:
                raise RuntimeError(f"El corte {nombre} falló (¿no toca material?)")
            self.md.ClearSelection2(True)
            f = s.cast(f, "IFeature").Name
        else:
            f = s.extruir(sk, hi - lo, md=self.md)
        return self._nom(f, nombre)

    def taladro(self, vista, ents, nombre=None):
        """Corte pasante en ambos sentidos desde el plano base de la vista (por el origen del grupo)."""
        sk = self._croquis(vista, ents, {"frontal": self.o[2], "lateral": self.o[0], "superior": self.o[1]}[vista])
        f = s.extruir(sk, 2000, corte=True, plano_medio=True, md=self.md)
        return self._nom(f, nombre)

    # -- revoluciones
    def rev(self, eje, c1, c2, perfil, corte=False, curva=False, anillo=False, nombre=None):
        """Sólido de revolución. eje 'y': vertical en (x=c1, a=c2). eje 'x': horizontal en (y=c1, a=c2).
        eje 'a': anteroposterior en (x=c1, y=c2). perfil = [(s, r)], s a lo largo del eje, r radio.
        curva=True une los puntos con una spline (aspecto orgánico)."""
        pts = list(perfil)
        smin, smax = min(p[0] for p in pts), max(p[0] for p in pts)
        if eje == "y":
            vista, c = "frontal", c2
            P = lambda q: (c1 + q[1], q[0]); A = lambda t: (c1, t)
        elif eje == "x":
            vista, c = "frontal", c2
            P = lambda q: (q[0], c1 + q[1]); A = lambda t: (t, c1)
        elif eje == "a":
            vista, c = "lateral", c1
            P = lambda q: (q[0], c2 + q[1]); A = lambda t: (t, c2)
        else:
            raise ValueError(eje)
        ents = []
        fuera = [q for q in pts if q[1] > 1e-9]
        if anillo:
            ents.append({"tipo": "polilinea", "puntos": [P(q) for q in pts]})
        elif curva and len(fuera) >= 3:
            ents.append({"tipo": "spline", "puntos": [P(q) for q in fuera]})
            a0, a1 = A(fuera[0][0]), A(fuera[-1][0])
            p0, p1 = P(fuera[0]), P(fuera[-1])
            ents.append({"tipo": "linea", "x1": p1[0], "y1": p1[1], "x2": a1[0], "y2": a1[1]})
            ents.append({"tipo": "linea", "x1": a1[0], "y1": a1[1], "x2": a0[0], "y2": a0[1]})
            ents.append({"tipo": "linea", "x1": a0[0], "y1": a0[1], "x2": p0[0], "y2": p0[1]})
        else:
            poli = []
            if pts[0][1] > 1e-9:
                poli.append(A(pts[0][0]))
            poli += [P(q) if q[1] > 1e-9 else A(q[0]) for q in pts]
            if pts[-1][1] > 1e-9:
                poli.append(A(pts[-1][0]))
            ents.append({"tipo": "polilinea", "puntos": poli})
        e0, e1 = A(smin - 4), A(smax + 4)
        ents.append({"tipo": "eje", "x1": e0[0], "y1": e0[1], "x2": e1[0], "y2": e1[1]})
        sk = self._croquis(vista, ents, c)
        f = s.revolucionar(sk, 360, corte=corte, md=self.md)
        return self._nom(f, nombre)

    def esfera(self, centro, r, nombre=None):
        x, y, a = centro
        ents = [{"tipo": "arco3", "x1": x, "y1": y + r, "x2": x, "y2": y - r, "x3": x + r, "y3": y},
                {"tipo": "linea", "x1": x, "y1": y - r, "x2": x, "y2": y + r},
                {"tipo": "eje", "x1": x, "y1": y - r - 4, "x2": x, "y2": y + r + 4}]
        sk = self._croquis("frontal", ents, a)
        f = s.revolucionar(sk, 360, md=self.md)
        return self._nom(f, nombre)

    # -- acabado
    def redondeo(self, radio, puntos):
        """puntos (x, y, a) del grupo sobre cada arista."""
        ox, oy, oa = self.o
        try:
            return s.redondeo(radio, [mundo((p[0] - ox, p[1] - oy, p[2] - oa)) for p in puntos], md=self.md)
        except Exception as e:  # noqa: BLE001
            print(f"  aviso: redondeo omitido en {self.nombre}: {e}")
            return None

    def terminar(self, color="hueso", material=None):
        if material:
            try:
                s.material(material, md=self.md)
            except Exception as e:  # noqa: BLE001
                print(f"  aviso: material {material} no aplicado a {self.nombre}: {e}")
        if color:
            rgb = COLOR.get(color, color)
            try:
                self.md.MaterialPropertyValues = s.arr([rgb[0], rgb[1], rgb[2], 1.0, 1.0, 0.4, 0.35, 0.0, 0.0])
            except Exception as e:  # noqa: BLE001
                print(f"  aviso: color no aplicado a {self.nombre}: {e}")
        for nombre_plano in self.planos.values():      # ocultar los planos auxiliares
            try:
                s.feature(nombre_plano, self.md).Select2(False, 0)
                self.md.BlankRefGeom()
            except Exception:  # noqa: BLE001
                pass
        self.md.ClearSelection2(True)
        self.md.ViewZoomtofit2()
        s.guardar(self.ruta)
        ABIERTOS.add(os.path.normcase(os.path.abspath(self.ruta)))
        info = s.masa(self.md)
        print(f"  pieza {self.nombre}: {info['masa_g']} g, caja {info['caja_mm_xyz']}")
        return {"ruta": self.ruta, "masa_g": info["masa_g"], "color": COLOR.get(color, color)}


def caja_pieza(md):
    """Caja envolvente (xmin, ymin, zmin, xmax, ymax, zmax) en mm, coordenadas de SolidWorks."""
    c = s.cast(md, "IPartDoc").GetPartBox(True)
    return [round(v / MM, 2) for v in c]


def exportar_stl(ruta_pieza, ruta_stl):
    sw = s.conectar()
    md = s.abrir(ruta_pieza)
    sw.ActivateDoc3(md.GetTitle(), False, 0, 0)
    return s.guardar(ruta_stl)


# ------------------------------------------------------------------ ensambles
def transformacion(R=None, t=(0.0, 0.0, 0.0)):
    """IMathTransform de SolidWorks. R: columnas = imágenes de los ejes locales (coordenadas SW).
    t en mm (coordenadas SW)."""
    R = R or IDENT
    mu = s.cast(s.conectar().GetMathUtility(), "IMathUtility")
    datos = [R[0][0], R[1][0], R[2][0], R[0][1], R[1][1], R[2][1], R[0][2], R[1][2], R[2][2],
             t[0] * MM, t[1] * MM, t[2] * MM, 1.0, 0.0, 0.0, 0.0]
    return s.cast(mu.CreateTransform(s.arr(datos)), "IMathTransform")


ABIERTOS = set()        # rutas de documentos que ya están cargados en SolidWorks en esta sesión


class Ensamble:
    def __init__(self, nombre, carpeta):
        self.nombre = nombre
        self.ruta = os.path.join(carpeta, nombre + ".SLDASM")
        self.md = s.nuevo("ensamble")
        self.asm = s.cast(self.md, "IAssemblyDoc")
        s.guardar(self.ruta)
        ABIERTOS.add(os.path.normcase(os.path.abspath(self.ruta)))
        self.titulo = self.md.GetTitle()
        self.comps = {}

    def activar(self):
        s.conectar().ActivateDoc3(self.titulo, False, 0, 0)

    def poner(self, ruta, R=None, t=(0.0, 0.0, 0.0), fijo=True, alias=None):
        """Inserta un archivo con giro R y traslación t (mm, coordenadas SW). Devuelve IComponent2."""
        sw = s.conectar()
        clave = os.path.normcase(os.path.abspath(ruta))
        if clave not in ABIERTOS:                      # el archivo debe estar cargado para insertarlo
            tipo = 1 if ruta.lower().endswith(".sldprt") else 2
            sw.OpenDoc6(ruta, tipo, s.K.swOpenDocOptions_Silent, "", 0, 0)
            ABIERTOS.add(clave)
        try:
            activo = s.cast(sw.ActiveDoc, "IModelDoc2").GetTitle()
        except Exception:  # noqa: BLE001
            activo = None
        if activo != self.titulo:
            self.activar()
        c = self.asm.AddComponent5(ruta, 0, "", False, "", 0.0, 0.0, 0.0)
        if c is None:
            raise RuntimeError(f"No se pudo insertar {ruta} en {self.nombre}")
        c = s.cast(c, "IComponent2")
        self.md.ClearSelection2(True)
        c.Select4(False, None, False)
        self.asm.UnfixComponent()
        c.Transform2 = transformacion(R, t)
        if fijo:
            self.md.ClearSelection2(True)
            c.Select4(False, None, False)
            self.asm.FixComponent()
        self.md.ClearSelection2(True)
        self.comps[alias or c.Name2] = c
        return c

    def componente(self, nombre_contiene):
        """Busca un componente (a cualquier nivel) cuyo Name2 contenga el texto."""
        for c in self.asm.GetComponents(False) or []:
            c = s.cast(c, "IComponent2")
            if nombre_contiene in c.Name2:
                return c
        raise KeyError(nombre_contiene)

    @staticmethod
    def _feat(comp, tipo, idx=0):
        f = comp.FirstFeature()
        n = 0
        while f is not None:
            f = s.cast(f, "IFeature")
            if f.GetTypeName2() == tipo:
                if n == idx:
                    return f
                n += 1
            f = f.GetNextFeature()
        raise KeyError(f"{tipo}[{idx}] en {comp.Name2}")

    def origen(self, comp):
        return self._feat(comp, "OriginProfileFeature")

    def plano(self, comp, cual):
        return self._feat(comp, "RefPlane", {"frontal": 0, "superior": 1, "lateral": 2}[cual])

    def relacion(self, tipo, e1, e2, nombre=None):
        """tipo: 'coincidente' o 'paralelo'. e1, e2: operaciones (IFeature) de componentes."""
        codigo = {"coincidente": 0, "paralelo": 3}[tipo]
        self.md.ClearSelection2(True)
        ok1 = e1.Select2(False, 1)
        ok2 = e2.Select2(True, 1)
        if not (ok1 and ok2):
            raise RuntimeError(f"No se pudieron seleccionar las entidades de la relación {nombre}")
        r = self.asm.AddMate5(codigo, 2, False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False, False, 0)
        m, err = (r if isinstance(r, tuple) else (r, 0))
        self.md.ClearSelection2(True)
        if m is None:
            raise RuntimeError(f"La relación {nombre} falló (error {err})")
        if nombre:
            try:
                s.cast(m, "IFeature").Name = nombre
            except Exception:  # noqa: BLE001
                pass
        return m

    def guardar(self):
        self.activar()
        self.md.EditRebuild3()
        self.md.ViewZoomtofit2()
        s.guardar(self.ruta)
        return self.ruta
