"""Puente Python <-> SolidWorks 2020 (API 28) por COM, con enlace temprano.

Todas las medidas que entran y salen de las funciones de alto nivel están en
MILÍMETROS y GRADOS; la API de SolidWorks trabaja en metros y radianes, así que
la conversión se hace aquí.

Las funciones deben llamarse siempre desde el mismo hilo (el servidor MCP usa
un único hilo COM). Para usarla en un script suelto basta con `import swlib`.
"""
from __future__ import annotations

import io
import math
import os
import re
import tempfile
import xml.etree.ElementTree as ET

import pythoncom
import win32com.client
from win32com.client import gencache, VARIANT

SWDIR = r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS"
MM = 0.001
DEG = math.pi / 180

_m = None          # módulo gen_py de sldworks.tlb
K = None           # constantes de swconst.tlb
_sw = None         # ISldWorks


# ---------------------------------------------------------------- conexión
def _parchear_qi():
    """SolidWorks no expone typeinfo: el IDispatch por defecto de un objeto no
    siempre es la interfaz que espera la clase gen_py (p. ej. IFeature). Hacemos
    QueryInterface a la interfaz correcta cada vez que gen_py envuelve un objeto."""
    base = win32com.client.DispatchBaseClass
    if getattr(base, "_sw_qi", False):
        return
    original = base.__init__

    def __init__(self, oobj=None):
        if isinstance(oobj, pythoncom.TypeIIDs[pythoncom.IID_IDispatch]):
            try:
                oobj = oobj.QueryInterface(self.CLSID, pythoncom.IID_IDispatch)
            except pythoncom.com_error:
                pass
        original(self, oobj)

    base.__init__ = __init__
    base._sw_qi = True


# Interfaz que devuelve cada método cuyo tipo no declara la typelib.
RETORNOS = {
    "ActiveDoc": "IModelDoc2", "NewDocument": "IModelDoc2", "OpenDoc6": "IModelDoc2",
    "OpenDoc7": "IModelDoc2", "GetFirstDocument": "IModelDoc2", "GetNext": "IModelDoc2",
    "ActivateDoc3": "IModelDoc2", "GetOpenDocumentByName": "IModelDoc2",
    "FirstFeature": "IFeature", "GetNextFeature": "IFeature", "FeatureByName": "IFeature",
    "FeatureByPositionReverse": "IFeature", "GetFirstSubFeature": "IFeature",
    "GetNextSubFeature": "IFeature", "GetSpecificFeature2": "IFeature", "GetFeature": "IFeature",
    "FeatureExtrusion3": "IFeature", "FeatureCut4": "IFeature", "FeatureRevolve2": "IFeature",
    "FeatureFillet3": "IFeature", "InsertFeatureChamfer": "IFeature", "InsertRefPlane": "IFeature",
    "FeatureCircularPattern4": "IFeature", "FeatureLinearPattern4": "IFeature",
    "InsertMirrorFeature2": "IFeature", "InsertSketch": None,
    "GetActiveSketch2": "ISketch", "GetSpecificFeature": "IFeature",
    "Parameter": "IDimension", "GetFirstFace": "IFace2", "GetNextFace": "IFace2",
    "AddComponent5": "IComponent2", "AddComponent4": "IComponent2", "AddMate5": "IMate2",
    "GetRootComponent3": "IComponent2", "GetModelDoc2": "IModelDoc2",
    "GetDefinition": None, "CreateMassProperty2": "IMassProperty2",
    "IGetActiveConfiguration": "IConfiguration", "GetActiveConfiguration": "IConfiguration",
}
# Para objetos sin entrada en RETORNOS se prueban estas interfaces en orden.
SONDEO = ["IFeature", "IFace2", "IEdge", "IBody2", "IVertex", "ISketchSegment", "ISketchPoint",
          "IComponent2", "IModelDoc2", "IDimension", "IDisplayDimension", "IMate2",
          "ISketch", "IRefPlane", "IConfiguration"]


def tipar(obj, pista: str | None = None):
    """Convierte un objeto COM genérico a su interfaz gen_py (por pista o sondeando QI)."""
    if obj is None or isinstance(obj, win32com.client.DispatchBaseClass):
        return obj
    m = _m
    raw = getattr(obj, "_oleobj_", obj)
    if not isinstance(raw, pythoncom.TypeIIDs[pythoncom.IID_IDispatch]):
        return obj
    interfaz = RETORNOS.get(pista) if pista else None
    candidatas = [interfaz] if interfaz else SONDEO
    for n in candidatas:
        cls = getattr(m, n, None)
        if cls is None:
            continue
        try:
            q = raw.QueryInterface(cls.CLSID, pythoncom.IID_IDispatch)
            return cls(q)
        except pythoncom.com_error:
            continue
    return win32com.client.dynamic.Dispatch(raw)


def _tipos():
    global _m, K
    if _m is None:
        _parchear_qi()
        a = pythoncom.LoadTypeLib(os.path.join(SWDIR, "sldworks.tlb")).GetLibAttr()
        _m = gencache.EnsureModule(str(a[0]), a[1], a[3], a[4])
        _original = _m.Dispatch

        def _dispatch_sw(ob, nombre=None, clsid=None, *a, **kw):
            if clsid is None:
                return tipar(ob, nombre)
            return _original(ob, nombre, clsid, *a, **kw)

        _m.Dispatch = _dispatch_sw
        c = pythoncom.LoadTypeLib(os.path.join(SWDIR, "swconst.tlb")).GetLibAttr()
        gencache.EnsureModule(str(c[0]), c[1], c[3], c[4])
        K = win32com.client.constants
    return _m


def conectar():
    """Devuelve ISldWorks. Se engancha a SolidWorks abierto o lo arranca."""
    global _sw
    m = _tipos()
    if _sw is not None:
        try:
            _sw.RevisionNumber()
            return _sw
        except Exception:
            _sw = None
    raw = pythoncom.CoCreateInstance("SldWorks.Application", None,
                                     pythoncom.CLSCTX_LOCAL_SERVER, pythoncom.IID_IDispatch)
    _sw = m.ISldWorks(raw)
    _sw.Visible = True
    return _sw


def cast(obj, interfaz: str):
    """Convierte un objeto COM genérico a la interfaz indicada ('IModelDoc2', 'IFeature'...)."""
    if obj is None:
        return None
    m = _tipos()
    raw = getattr(obj, "_oleobj_", obj)
    return getattr(m, interfaz)(raw)


def arr(valores, vt=pythoncom.VT_R8):
    """Arreglo COM tipado (por defecto de dobles) para métodos que piden VARIANT."""
    return VARIANT(pythoncom.VT_ARRAY | vt, list(valores))


NADA = VARIANT(pythoncom.VT_DISPATCH, None)


# ---------------------------------------------------------------- documentos
def doc():
    """Documento activo como IModelDoc2 (error si no hay ninguno)."""
    d = conectar().ActiveDoc
    if d is None:
        raise RuntimeError("No hay ningún documento abierto en SolidWorks.")
    return cast(d, "IModelDoc2")


def pieza():
    return cast(doc(), "IPartDoc")


def ensamble():
    return cast(doc(), "IAssemblyDoc")


TIPOS_DOC = {1: "pieza", 2: "ensamble", 3: "dibujo"}


def nuevo(tipo: str = "pieza"):
    sw = conectar()
    pref = {"pieza": K.swDefaultTemplatePart, "ensamble": K.swDefaultTemplateAssembly,
            "dibujo": K.swDefaultTemplateDrawing}[tipo]
    plantilla = sw.GetUserPreferenceStringValue(pref)
    d = sw.NewDocument(plantilla, 0, 0, 0)
    if d is None:
        raise RuntimeError(f"No se pudo crear el documento con la plantilla {plantilla}")
    md = cast(d, "IModelDoc2")
    # milímetros, gramos, segundos
    md.Extension.SetUserPreferenceInteger(K.swUnitSystem, 0, K.swUnitSystem_MMGS)
    return md


def abrir(ruta: str):
    sw = conectar()
    ext = os.path.splitext(ruta)[1].lower()
    tipo = {".sldprt": 1, ".sldasm": 2, ".slddrw": 3}.get(ext)
    if tipo is None:
        raise ValueError("Solo .sldprt, .sldasm o .slddrw")
    d, err, warn = sw.OpenDoc6(ruta, tipo, K.swOpenDocOptions_Silent, "", 0, 0)
    if d is None:
        raise RuntimeError(f"No se pudo abrir {ruta} (error {err})")
    return cast(d, "IModelDoc2")


def guardar(ruta: str | None = None):
    """Guarda el documento activo. Si ruta termina en .stl/.step/.igs/.x_t/.3mf, exporta una copia."""
    md = doc()
    if ruta is None:
        if not md.GetPathName():
            raise ValueError("El documento nunca se guardó: indica una ruta .sldprt/.sldasm")
        ok = md.Save3(K.swSaveAsOptions_Silent, 0, 0)
        return md.GetPathName()
    ruta = os.path.abspath(ruta)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    ext = os.path.splitext(ruta)[1].lower()
    nativo = ext in (".sldprt", ".sldasm", ".slddrw")
    opciones = K.swSaveAsOptions_Silent | (0 if nativo else K.swSaveAsOptions_Copy)
    err = md.SaveAs3(ruta, 0, opciones)
    if err != 0 or not os.path.exists(ruta):
        raise RuntimeError(f"SaveAs falló (código {err}) para {ruta}. Suele pasar si otro "
                           "documento abierto en SolidWorks ya usa ese nombre o la carpeta no "
                           "tiene permisos de escritura.")
    return ruta


# ---------------------------------------------------------------- árbol
def features(md=None):
    md = md or doc()
    f = md.FirstFeature()
    out = []
    while f is not None:
        out.append(f)
        f = f.GetNextFeature()
    return out


def arbol(md=None, solo_usuario=True):
    """Lista [(nombre, tipo)] del árbol. Con solo_usuario, desde el origen en adelante."""
    md = md or doc()
    lista = []
    visto_origen = not solo_usuario
    for f in features(md):
        t = f.GetTypeName2()
        if visto_origen:
            lista.append((f.Name, t))
        if t == "OriginProfileFeature":
            visto_origen = True
    return lista


def planos_base(md=None):
    """Los tres planos de la plantilla en orden: alzado (XY), planta (XZ), lateral (YZ)."""
    md = md or doc()
    p = [f for f in features(md) if f.GetTypeName2() == "RefPlane"]
    return p[:3]


ALIAS_PLANO = {
    "frontal": 0, "front": 0, "alzado": 0, "xy": 0,
    "superior": 1, "top": 1, "planta": 1, "xz": 1,
    "lateral": 2, "derecho": 2, "right": 2, "vista lateral": 2, "yz": 2,
}


def feature(nombre: str, md=None):
    md = md or doc()
    tipo = md.GetType()
    f = None
    if tipo in (1, 2):
        f = cast(md, "IPartDoc" if tipo == 1 else "IAssemblyDoc").FeatureByName(nombre)
    if f is None:
        f = next((x for x in features(md) if x.Name == nombre), None)
    if f is None:
        raise ValueError(f"No existe la operación '{nombre}'")
    return cast(f, "IFeature")


def ultima_feature(md=None):
    md = md or doc()
    return cast(md.FeatureByPositionReverse(0), "IFeature")


# ---------------------------------------------------------------- selección
def limpiar_seleccion(md=None):
    (md or doc()).ClearSelection2(True)


TOLERANCIA_SEL_MM = 0.5


def entidad_cercana(tipo: str, x: float, y: float, z: float, md=None):
    """Cara (tipo FACE) o arista (EDGE) de los sólidos de la pieza más cercana al punto
    (x,y,z) en mm. Devuelve (entidad, distancia_mm), o (None, inf) si no hay sólidos."""
    md = md or doc()
    p = (x * MM, y * MM, z * MM)
    interfaz = "IFace2" if tipo == "FACE" else "IEdge"
    mejor, dmin = None, math.inf
    for b in cast(md, "IPartDoc").GetBodies2(0, True) or []:   # 0 = swSolidBody
        b = cast(b, "IBody2")
        for e in (b.GetFaces() if tipo == "FACE" else b.GetEdges()) or []:
            e = cast(e, interfaz)
            q = e.GetClosestPointOn(*p)
            if not q:
                continue
            d = math.dist(p, q[:3])
            if d < dmin:
                mejor, dmin = e, d
    return mejor, dmin / MM


def _seleccionar_geom(tipo, x, y, z, agregar, marca, md):
    """Selección de caras/aristas por geometría, sin depender de la vista activa.
    SelectByID2 lanza un rayo según la cámara y falla si la cara queda de canto."""
    e, d = entidad_cercana(tipo, x, y, z, md)
    if e is None:
        return False
    if d > TOLERANCIA_SEL_MM:
        nombre = "cara" if tipo == "FACE" else "arista"
        raise RuntimeError(f"No hay ninguna {nombre} en ({x}, {y}, {z}) mm: "
                           f"la más cercana está a {d:.2f} mm.")
    sm = cast(md.SelectionManager, "ISelectionMgr")
    sd = cast(sm.CreateSelectData(), "ISelectData")
    sd.Mark = marca
    return bool(cast(e, "IEntity").Select4(agregar, sd))


def seleccionar(nombre: str, tipo: str, x=0.0, y=0.0, z=0.0, agregar=False, marca=0, md=None):
    """Selecciona por nombre/tipo o por punto (x,y,z en mm). tipo: PLANE, SKETCH, FACE, EDGE, BODYFEATURE...
    En piezas, FACE y EDGE por punto se buscan por geometría (no dependen de la vista)."""
    md = md or doc()
    if not nombre and tipo in ("FACE", "EDGE") and md.GetType() == 1:
        if _seleccionar_geom(tipo, x, y, z, agregar, marca, md):
            return True
    ok = md.Extension.SelectByID2(nombre, tipo, x * MM, y * MM, z * MM, agregar, marca, None, 0)
    if not ok:
        donde = f"'{nombre}'" if nombre else f"en ({x}, {y}, {z}) mm"
        raise RuntimeError(f"No se pudo seleccionar {tipo} {donde}")
    return True


def seleccionar_plano(plano: str, md=None, agregar=False, marca=0):
    md = md or doc()
    idx = ALIAS_PLANO.get(plano.strip().lower())
    f = planos_base(md)[idx] if idx is not None else feature(plano, md)
    if not f.Select2(agregar, marca):
        raise RuntimeError(f"No se pudo seleccionar el plano {plano}")
    return f.Name


# ---------------------------------------------------------------- croquis
def _entidad(sm, e: dict):
    t = e["tipo"].lower()
    g = lambda k, d=0.0: float(e.get(k, d)) * MM
    if t in ("circulo", "círculo", "circle"):
        return sm.CreateCircleByRadius(g("x"), g("y"), 0, g("r"))
    if t in ("rectangulo", "rectángulo", "rect"):
        if "ancho" in e:   # centrado
            cx, cy, w, h = g("x"), g("y"), g("ancho") / 2, g("alto") / 2
            return sm.CreateCenterRectangle(cx, cy, 0, cx + w, cy + h, 0)
        return sm.CreateCornerRectangle(g("x1"), g("y1"), 0, g("x2"), g("y2"), 0)
    if t in ("linea", "línea", "line"):
        return sm.CreateLine(g("x1"), g("y1"), 0, g("x2"), g("y2"), 0)
    if t in ("eje", "centerline", "linea_constructiva"):
        return sm.CreateCenterLine(g("x1"), g("y1"), 0, g("x2"), g("y2"), 0)
    if t in ("polilinea", "polilínea", "poligono_libre", "polyline"):
        pts = [(float(p[0]) * MM, float(p[1]) * MM) for p in e["puntos"]]
        if e.get("cerrada", True) and pts[0] != pts[-1]:
            pts.append(pts[0])
        segs = []
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            segs.append(sm.CreateLine(x1, y1, 0, x2, y2, 0))
        return segs
    if t in ("arco", "arc"):
        # arco por centro, punto inicial, punto final; sentido 1 = antihorario, -1 = horario
        return sm.CreateArc(g("cx"), g("cy"), 0, g("x1"), g("y1"), 0, g("x2"), g("y2"), 0,
                            int(e.get("sentido", 1)))
    if t in ("arco3", "arco_3p"):
        return sm.Create3PointArc(g("x1"), g("y1"), 0, g("x2"), g("y2"), 0, g("x3"), g("y3"), 0)
    if t in ("ranura", "slot"):
        return sm.CreateSketchSlot(K.swSketchSlotCreationType_line, K.swSketchSlotLengthType_CenterCenter,
                                   g("ancho"), g("x1"), g("y1"), 0, g("x2"), g("y2"), 0, 0, 0, 0, 1, False)
    if t in ("poligono", "polígono", "polygon"):
        n = int(e["lados"]); r = g("r"); cx, cy = g("x"), g("y")
        ang = float(e.get("angulo", 90)) * DEG
        return sm.CreatePolygon(cx, cy, 0, cx + r * math.cos(ang), cy + r * math.sin(ang), 0, n, True)
    if t in ("spline", "curva"):
        pts = []
        for p in e["puntos"]:
            pts += [float(p[0]) * MM, float(p[1]) * MM, 0.0]
        return sm.CreateSpline2(arr(pts), True)
    if t in ("elipse", "ellipse"):
        cx, cy = g("x"), g("y")
        return sm.CreateEllipse(cx, cy, 0, cx + g("rx"), cy, 0, cx, cy + g("ry"), 0)
    raise ValueError(f"Tipo de entidad desconocido: {e['tipo']}")


def croquis(entidades: list[dict], plano: str = "frontal", en_cara: tuple | None = None, md=None):
    """Crea un croquis y devuelve su nombre.

    plano: frontal/superior/lateral o el nombre de un plano o croquis.
    en_cara: (x, y, z) en mm de un punto sobre una cara plana; tiene prioridad sobre `plano`.
    Coordenadas de las entidades en mm, en el sistema del croquis.
    """
    md = md or doc()
    limpiar_seleccion(md)
    if en_cara is not None:
        seleccionar("", "FACE", *en_cara, md=md)
    else:
        seleccionar_plano(plano, md)
    sm = md.SketchManager
    sm.InsertSketch(True)
    sm.AddToDB = True
    sm.DisplayWhenAdded = False
    try:
        for e in entidades:
            r = _entidad(sm, e)
            if r is None:
                raise RuntimeError(f"SolidWorks no creó la entidad {e}")
    finally:
        sm.AddToDB = False
        sm.DisplayWhenAdded = True
        sm.InsertSketch(True)
    f = ultima_feature(md)
    md.ClearSelection2(True)
    return f.Name


def _seleccionar_croquis(nombre, md, marca=0):
    limpiar_seleccion(md)
    f = feature(nombre, md)
    if not f.Select2(False, marca):
        raise RuntimeError(f"No se pudo seleccionar el croquis {nombre}")


# ---------------------------------------------------------------- operaciones
FIN = {"ciega": 0, "pasante": 1, "hasta_siguiente": 2, "plano_medio": 6, "pasante_ambos": 9}


def extruir(croquis_nombre: str, profundidad: float = 10, invertir=False, plano_medio=False,
            corte=False, pasante=False, profundidad2: float | None = None, fusionar=True, md=None):
    """Extruye (o corta) un croquis. profundidad en mm. Devuelve el nombre de la operación."""
    md = md or doc()
    _seleccionar_croquis(croquis_nombre, md)
    fm = md.FeatureManager
    if plano_medio:
        t1 = K.swEndCondMidPlane
    elif pasante:
        t1 = K.swEndCondThroughAll
    else:
        t1 = K.swEndCondBlind
    dos = profundidad2 is not None
    d1, d2 = profundidad * MM, (profundidad2 or 0) * MM
    t2 = K.swEndCondBlind
    if corte:
        f = fm.FeatureCut4(not dos, invertir, False, t1, t2, d1, d2,
                           False, False, False, False, 0, 0, False, False, False, False,
                           False, True, True, True, True, False,
                           0, 0, False, False)
    else:
        f = fm.FeatureExtrusion3(not dos, invertir, False, t1, t2, d1, d2,
                                 False, False, False, False, 0, 0, False, False, False, False,
                                 fusionar, True, True, 0, 0, False)
    if f is None:
        raise RuntimeError("La extrusión falló: revisa que el croquis esté cerrado "
                           "y, si es un corte, que toque material.")
    md.ClearSelection2(True)
    return cast(f, "IFeature").Name


def revolucionar(croquis_nombre: str, angulo: float = 360, corte=False, invertir=False,
                 fusionar=True, md=None):
    """Revoluciona un croquis alrededor de su línea constructiva ('eje')."""
    md = md or doc()
    _seleccionar_croquis(croquis_nombre, md)
    fm = md.FeatureManager
    f = fm.FeatureRevolve2(True, True, False, corte, invertir, False,
                           K.swEndCondBlind, K.swEndCondBlind, angulo * DEG, 0,
                           False, False, 0, 0, 0, 0, 0, fusionar, True, True)
    if f is None:
        raise RuntimeError("La revolución falló: el croquis necesita un perfil cerrado y "
                           "UNA línea constructiva (tipo 'eje') que no lo cruce.")
    md.ClearSelection2(True)
    return cast(f, "IFeature").Name


def redondeo(radio: float, aristas: list, md=None):
    """Redondea aristas. aristas = lista de puntos [x,y,z] en mm que estén sobre cada arista."""
    md = md or doc()
    limpiar_seleccion(md)
    for i, p in enumerate(aristas):
        seleccionar("", "EDGE", *p, agregar=i > 0, marca=1, md=md)
    fm = md.FeatureManager
    f = fm.FeatureFillet3(195, radio * MM, 0, 0, 0, 0, 0,
                          NADA_V(), NADA_V(), NADA_V(), NADA_V(), NADA_V(), NADA_V(), NADA_V())
    if f is None:
        raise RuntimeError("El redondeo falló (radio demasiado grande o arista no válida).")
    md.ClearSelection2(True)
    return cast(f, "IFeature").Name


def NADA_V():
    return VARIANT(pythoncom.VT_EMPTY, None)


def chaflan(distancia: float, aristas: list, angulo: float = 45, md=None):
    md = md or doc()
    limpiar_seleccion(md)
    for i, p in enumerate(aristas):
        seleccionar("", "EDGE", *p, agregar=i > 0, marca=1, md=md)
    f = md.FeatureManager.InsertFeatureChamfer(4, K.swChamferAngleDistance, distancia * MM,
                                               angulo * DEG, 0, 0, 0, 0)
    if f is None:
        raise RuntimeError("El chaflán falló.")
    md.ClearSelection2(True)
    return cast(f, "IFeature").Name


def vaciado(espesor: float, caras_abiertas: list, hacia_afuera=False, md=None):
    """Vaciado (shell). caras_abiertas = puntos [x,y,z] mm sobre las caras que se eliminan."""
    md = md or doc()
    limpiar_seleccion(md)
    for i, p in enumerate(caras_abiertas):
        seleccionar("", "FACE", *p, agregar=i > 0, md=md)
    antes = ultima_feature(md).Name
    md.InsertFeatureShell(espesor * MM, hacia_afuera)
    despues = ultima_feature(md).Name
    if despues == antes:
        raise RuntimeError("El vaciado falló.")
    md.ClearSelection2(True)
    return despues


def patron_circular(operaciones: list[str], eje: str, cantidad: int, angulo_total=360, md=None):
    """Patrón circular de operaciones alrededor de un eje (nombre de un eje o arista circular)."""
    md = md or doc()
    limpiar_seleccion(md)
    seleccionar(eje, "AXIS", marca=1, md=md)
    for n in operaciones:
        feature(n, md).Select2(True, 4)
    f = md.FeatureManager.FeatureCircularPattern4(cantidad, angulo_total * DEG, False, "NULL",
                                                  False, True, False)
    if f is None:
        raise RuntimeError("El patrón circular falló.")
    md.ClearSelection2(True)
    return cast(f, "IFeature").Name


def eje(plano1: str, plano2: str, md=None):
    """Eje de referencia en la intersección de dos planos."""
    md = md or doc()
    limpiar_seleccion(md)
    seleccionar_plano(plano1, md)
    seleccionar_plano(plano2, md, agregar=True)
    if not md.InsertAxis2(True):
        raise RuntimeError("No se pudo crear el eje.")
    md.ClearSelection2(True)
    return ultima_feature(md).Name


def plano_desfasado(plano: str, distancia: float, md=None):
    md = md or doc()
    limpiar_seleccion(md)
    seleccionar_plano(plano, md, marca=0)
    base = feature(nombre_plano(plano, md), md)

    def crear(voltear):
        seleccionar_plano(plano, md)
        restr = K.swRefPlaneReferenceConstraint_Distance
        if voltear:
            restr |= K.swRefPlaneReferenceConstraint_OptionFlip
        if md.FeatureManager.InsertRefPlane(restr, abs(distancia) * MM, 0, 0, 0, 0) is None:
            raise RuntimeError("No se pudo crear el plano.")
        md.ClearSelection2(True)
        return ultima_feature(md)

    nuevo_f = crear(False)
    # comprobar el lado: desplazamiento con signo a lo largo de la normal del plano base
    ob, nb = _plano_geom(base)
    on, _ = _plano_geom(nuevo_f)
    lado = sum((on[i] - ob[i]) * nb[i] for i in range(3))
    if distancia != 0 and (lado > 0) != (distancia > 0):
        borrar(nuevo_f.Name, md)
        nuevo_f = crear(True)
    return nuevo_f.Name


def _plano_geom(f):
    """(origen, normal) de un plano de referencia, en metros."""
    rp = tipar(f.GetSpecificFeature2(), None)
    rp = cast(rp, "IRefPlane")
    d = rp.Transform.ArrayData
    return (d[9], d[10], d[11]), (d[6], d[7], d[8])


def nombre_plano(plano: str, md=None):
    idx = ALIAS_PLANO.get(plano.strip().lower())
    return planos_base(md)[idx].Name if idx is not None else plano


def suprimir(nombre: str, suprimir_=True, md=None):
    md = md or doc()
    feature(nombre, md).Select2(False, 0)
    ok = md.EditSuppress2() if suprimir_ else md.EditUnsuppress2()
    md.ClearSelection2(True)
    return ok


def borrar(nombre: str, md=None):
    md = md or doc()
    limpiar_seleccion(md)
    feature(nombre, md).Select2(False, 0)
    ok = md.Extension.DeleteSelection2(K.swDelete_Absorbed)
    md.ClearSelection2(True)
    return ok


def cota(nombre_cota: str, valor_mm: float | None = None, md=None):
    """Lee o cambia una cota tipo 'D1@Croquis1' / 'D1@Extruir1'. Devuelve el valor en mm."""
    md = md or doc()
    d = cast(md.Parameter(nombre_cota), "IDimension")
    if d is None:
        raise ValueError(f"No existe la cota {nombre_cota}")
    if valor_mm is not None:
        d.SetSystemValue3(valor_mm * MM, K.swSetValue_InThisConfiguration, None)
        md.EditRebuild3()
    return d.GetSystemValue3(K.swThisConfiguration, None)[0] / MM


def deshacer(pasos: int = 1, md=None):
    (md or doc()).EditUndo2(pasos)


# ---------------------------------------------------------------- material y masa
_MATS = None


def _catalogo():
    """[(clase_es, nombre_es, nombre_en)]. La API exige el nombre inglés aunque la UI esté en español;
    se emparejan por 'matid'."""
    global _MATS
    if _MATS is None:
        def leer(idioma):
            p = os.path.join(SWDIR, "lang", idioma, "sldmaterials", "solidworks materials.sldmat")
            if not os.path.exists(p):
                return {}
            d = {}
            for clase in ET.parse(p).getroot().iter("classification"):
                for mat in clase.iter("material"):
                    d[(mat.get("matid"))] = (clase.get("name"), mat.get("name"))
            return d
        en, es = leer("english"), leer("spanish") or {}
        _MATS = []
        for mid, (clase_en, n_en) in en.items():
            clase_es, n_es = es.get(mid, (clase_en, n_en))
            _MATS.append((clase_es, n_es, n_en))
    return _MATS


def materiales(buscar: str = ""):
    """Lista [(clase, nombre_es, nombre_en)] que contengan `buscar` (en cualquier idioma o clase)."""
    b = buscar.lower()
    return [m for m in _catalogo() if not b or any(b in x.lower() for x in m)]


def material(nombre: str, md=None):
    """Asigna material por nombre en español o inglés. Devuelve el nombre inglés aplicado."""
    md = md or doc()
    p = cast(md, "IPartDoc")
    ingles = next((en for _, es, en in _catalogo() if nombre.lower() in (es.lower(), en.lower())), nombre)
    p.SetMaterialPropertyName2("", "SOLIDWORKS Materials", ingles)
    nm = p.GetMaterialPropertyName2("")
    nombre_actual = nm[0] if isinstance(nm, tuple) else nm
    if not nombre_actual or nombre_actual.lower() != ingles.lower():
        raise RuntimeError(f"No se aplicó el material '{nombre}'. Busca el nombre exacto con "
                           f"sw_materiales('{nombre[:4]}').")
    return nombre_actual


def masa(md=None):
    md = md or doc()
    md.EditRebuild3()
    mp = md.Extension.CreateMassProperty()
    if mp is None:
        raise RuntimeError("No hay sólidos para calcular propiedades de masa.")
    mp.UseSystemUnits = True
    c = mp.CenterOfMass
    bb = None
    try:
        p = cast(md, "IPartDoc")
        caja = p.GetPartBox(True)
        bb = [round((caja[i + 3] - caja[i]) / MM, 2) for i in range(3)]
    except Exception:
        pass
    return {
        "masa_g": round(mp.Mass * 1000, 3),
        "volumen_cm3": round(mp.Volume * 1e6, 3),
        "area_cm2": round(mp.SurfaceArea * 1e4, 3),
        "centro_masa_mm": [round(v / MM, 3) for v in c],
        "densidad_kg_m3": round(mp.Density, 1),
        "caja_mm_xyz": bb,
    }


# ---------------------------------------------------------------- vista
VISTAS = {"frontal": 1, "posterior": 2, "izquierda": 3, "derecha": 4, "superior": 5,
          "inferior": 6, "isometrica": 7, "isométrica": 7, "trimetrica": 8, "dimetrica": 9}


def captura(vista: str = "isometrica", ancho: int = 1000, alto: int = 750, ajustar=True, md=None) -> bytes:
    """Devuelve un PNG de la vista indicada del documento activo."""
    from PIL import Image
    md = md or doc()
    v = VISTAS.get(vista.lower())
    if v is not None:
        md.ShowNamedView2("", v)
    if ajustar:
        md.ViewZoomtofit2()
    md.GraphicsRedraw2()
    tmp = os.path.join(tempfile.gettempdir(), "sw_captura.bmp")
    if os.path.exists(tmp):
        os.remove(tmp)
    # SaveBMP a tamaño distinto de la ventana descentra el encuadre: capturamos
    # al tamaño real del área gráfica y luego escalamos.
    try:
        v = md.ActiveView
        w, h = int(v.FrameWidth), int(v.FrameHeight)
    except Exception:
        w, h = 0, 0
    if w < 50 or h < 50:
        w, h = ancho, alto
    if not md.SaveBMP(tmp, w, h) or not os.path.exists(tmp):
        raise RuntimeError("SolidWorks no pudo guardar la captura (¿ventana minimizada?).")
    img = Image.open(tmp).convert("RGB")
    if ajustar:
        # recortar alrededor de la geometría (aristas y caras son más oscuras que el fondo)
        mascara = img.convert("L").point(lambda p: 255 if p < 205 else 0)
        caja = mascara.getbbox()
        if caja:
            x0, y0, x1, y1 = caja
            margen = int(0.08 * max(x1 - x0, y1 - y0)) + 10
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            w2 = (x1 - x0) / 2 + margen
            h2 = (y1 - y0) / 2 + margen
            # conservar la proporción pedida
            if w2 / h2 < ancho / alto:
                w2 = h2 * ancho / alto
            else:
                h2 = w2 * alto / ancho
            fondo = img.getpixel((2, 2))
            lienzo = Image.new("RGB", (int(2 * w2), int(2 * h2)), fondo)
            lienzo.paste(img, (int(w2 - cx), int(h2 - cy)))
            img = lienzo
    img = img.resize((ancho, alto), Image.LANCZOS) if img.size != (ancho, alto) else img
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------- ensamble
def insertar_componente(ruta: str, x=0.0, y=0.0, z=0.0, md=None):
    """Inserta una pieza/ensamble guardado en el ensamble activo. Devuelve el nombre del componente."""
    sw = conectar()
    md = md or doc()
    titulo = md.GetTitle()
    # el archivo debe estar abierto para AddComponent
    ext = os.path.splitext(ruta)[1].lower()
    tipo = 1 if ext == ".sldprt" else 2
    sw.OpenDoc6(ruta, tipo, K.swOpenDocOptions_Silent, "", 0, 0)
    sw.ActivateDoc3(titulo, False, 0, 0)
    asm = cast(conectar().ActiveDoc, "IAssemblyDoc")
    c = asm.AddComponent5(ruta, 0, "", False, "", x * MM, y * MM, z * MM)
    if c is None:
        raise RuntimeError(f"No se pudo insertar {ruta}")
    return cast(c, "IComponent2").Name2


def info():
    sw = conectar()
    docs = []
    d = sw.GetFirstDocument()
    while d is not None:
        md = cast(d, "IModelDoc2")
        docs.append({"titulo": md.GetTitle(), "tipo": TIPOS_DOC.get(md.GetType(), md.GetType()),
                     "ruta": md.GetPathName()})
        d = md.GetNext()
    act = sw.ActiveDoc
    return {"version": sw.RevisionNumber(), "activo": cast(act, "IModelDoc2").GetTitle() if act else None,
            "documentos": docs}
