"""Servidor MCP: Claude <-> SolidWorks 2020 (COM).

Arranque (lo hace Claude Code solo, vía .mcp.json):
    .venv\\Scripts\\python.exe server.py
"""
from __future__ import annotations

import asyncio
import contextlib
import io
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pythoncom

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swlib as s  # noqa: E402

from mcp.server.mcpserver import MCPServer, Image  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

INSTRUCCIONES = """\
Controla el SolidWorks 2020 abierto en esta PC (se lanza solo si está cerrado).

Unidades: TODO en milímetros y grados. Ejes del modelo: X derecha, Y arriba, Z hacia el frente.
Planos: 'frontal' (XY), 'superior' (XZ), 'lateral' (YZ); también vale el nombre de cualquier
plano creado (p. ej. 'Plane1'). Coordenadas de croquis: en 'frontal' x=X, y=Y; en 'superior'
x=X, y=-Z; en 'lateral' x=-Z, y=Y. Para croquizar sobre una cara usa en_cara=[x,y,z] (un punto
del modelo que caiga sobre esa cara plana); las coordenadas del croquis quedan en el sistema
de esa cara, por eso conviene comprobar con sw_ver.

Flujo típico: sw_nuevo -> sw_croquis -> sw_extruir/sw_revolucion -> sw_redondeo -> sw_ver
(mira el resultado SIEMPRE tras cambios de geometría) -> sw_material -> sw_masa -> sw_guardar.
Las aristas y caras se eligen por un punto [x,y,z] en mm que esté sobre ellas.
Las cotas se llaman como en SolidWorks: 'D1@Sketch1', 'D1@Boss-Extrude1'.

Para lo que no cubran las herramientas (relaciones de posición, ecuaciones, configuraciones,
dibujos, chapa...), usa sw_python: ejecuta Python con la API COM completa de SolidWorks.
"""

mcp = MCPServer("solidworks", instructions=INSTRUCCIONES)

# Un único hilo COM: SolidWorks no tolera llamadas desde hilos distintos.
_hilo = ThreadPoolExecutor(max_workers=1, initializer=pythoncom.CoInitialize,
                           thread_name_prefix="com-sw")


async def _en_com(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()

    def envoltura():
        # ToolError hace que el mensaje real llegue a Claude (si no, MCP lo oculta).
        try:
            return fn(*args, **kwargs)
        except pythoncom.com_error as e:
            raise ToolError(f"Error COM de SolidWorks: {e}") from e
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"{type(e).__name__}: {e}") from e

    return await loop.run_in_executor(_hilo, envoltura)


def _con_arbol(resultado: dict) -> dict:
    try:
        resultado["arbol"] = [n for n, _ in s.arbol()][-12:]
    except Exception:
        pass
    return resultado


# ------------------------------------------------------------------ documentos
@mcp.tool()
async def sw_estado() -> dict:
    """Versión de SolidWorks, documentos abiertos, documento activo y su árbol de operaciones."""
    def f():
        i = s.info()
        if i["activo"]:
            i["arbol"] = [{"nombre": n, "tipo": t} for n, t in s.arbol()]
            i["tipo_activo"] = s.TIPOS_DOC.get(s.doc().GetType())
        return i
    return await _en_com(f)


@mcp.tool()
async def sw_nuevo(tipo: str = "pieza") -> str:
    """Crea un documento nuevo ('pieza' o 'ensamble') en unidades MMGS. Devuelve su título."""
    return await _en_com(lambda: s.nuevo(tipo).GetTitle())


@mcp.tool()
async def sw_abrir(ruta: str) -> str:
    """Abre un .sldprt/.sldasm/.slddrw existente y lo deja activo."""
    return await _en_com(lambda: s.abrir(ruta).GetTitle())


@mcp.tool()
async def sw_activar(titulo: str) -> str:
    """Activa otro documento abierto por su título (ver sw_estado)."""
    def f():
        s.conectar().ActivateDoc3(titulo, False, 0, 0)
        return s.doc().GetTitle()
    return await _en_com(f)


@mcp.tool()
async def sw_guardar(ruta: str | None = None) -> str:
    """Guarda el documento activo. Sin ruta: guarda en su sitio. Con ruta .sldprt/.sldasm: guarda como.
    Con .stl, .step, .igs, .x_t, .3mf o .pdf: exporta una copia (el documento sigue igual)."""
    return await _en_com(lambda: s.guardar(ruta))


# ------------------------------------------------------------------ croquis y operaciones
@mcp.tool()
async def sw_croquis(entidades: list[dict[str, Any]], plano: str = "frontal",
                     en_cara: list[float] | None = None) -> dict:
    """Crea un croquis y devuelve su nombre. Medidas en mm.

    Tipos de entidad (campo 'tipo'):
      circulo {x,y,r} | rectangulo {x,y,ancho,alto} (centrado) o {x1,y1,x2,y2} (esquinas)
      linea {x1,y1,x2,y2} | eje {x1,y1,x2,y2} (línea constructiva, para revoluciones)
      polilinea {puntos:[[x,y],...], cerrada:true} | arco {cx,cy,x1,y1,x2,y2,sentido:1|-1}
      arco3 {x1,y1,x2,y2,x3,y3} | ranura {x1,y1,x2,y2,ancho} | poligono {x,y,r,lados}
      spline {puntos:[[x,y],...]} | elipse {x,y,rx,ry}
    plano: frontal | superior | lateral | nombre de un plano. en_cara: [x,y,z] sobre una cara plana.
    """
    return await _en_com(lambda: _con_arbol(
        {"croquis": s.croquis(entidades, plano, tuple(en_cara) if en_cara else None)}))


@mcp.tool()
async def sw_extruir(croquis: str, profundidad_mm: float = 10, corte: bool = False,
                     pasante: bool = False, plano_medio: bool = False, invertir: bool = False,
                     profundidad2_mm: float | None = None) -> dict:
    """Extruye un croquis (o lo corta con corte=true). pasante=true atraviesa todo.
    plano_medio=true reparte la profundidad a ambos lados. profundidad2_mm extruye también
    en sentido contrario. invertir cambia el sentido.
    Sentido por defecto: la extrusión sale hacia la normal del croquis (frontal +Z, superior +Y,
    lateral +X) y el corte va al revés, contra la normal (desde 'superior' corta hacia -Y).
    Los croquis no llevan cotas: solo se pueden cambiar con sw_cota las de las operaciones."""
    return await _en_com(lambda: _con_arbol({"operacion": s.extruir(
        croquis, profundidad_mm, invertir=invertir, plano_medio=plano_medio, corte=corte,
        pasante=pasante, profundidad2=profundidad2_mm)}))


@mcp.tool()
async def sw_revolucion(croquis: str, angulo: float = 360, corte: bool = False,
                        invertir: bool = False) -> dict:
    """Revoluciona un croquis alrededor de su línea 'eje'. Ideal para ejes, bujes, falanges."""
    return await _en_com(lambda: _con_arbol(
        {"operacion": s.revolucionar(croquis, angulo, corte=corte, invertir=invertir)}))


@mcp.tool()
async def sw_redondeo(radio_mm: float, aristas: list[list[float]]) -> dict:
    """Redondea aristas. aristas: lista de puntos [x,y,z] mm, cada uno sobre una arista."""
    return await _en_com(lambda: _con_arbol({"operacion": s.redondeo(radio_mm, aristas)}))


@mcp.tool()
async def sw_chaflan(distancia_mm: float, aristas: list[list[float]], angulo: float = 45) -> dict:
    """Chaflán distancia-ángulo en las aristas indicadas por puntos [x,y,z] mm."""
    return await _en_com(lambda: _con_arbol({"operacion": s.chaflan(distancia_mm, aristas, angulo)}))


@mcp.tool()
async def sw_vaciado(espesor_mm: float, caras_abiertas: list[list[float]],
                     hacia_afuera: bool = False) -> dict:
    """Vaciado (shell) con espesor de pared; caras_abiertas: puntos [x,y,z] mm de las caras a quitar."""
    return await _en_com(lambda: _con_arbol(
        {"operacion": s.vaciado(espesor_mm, caras_abiertas, hacia_afuera)}))


@mcp.tool()
async def sw_plano(base: str, distancia_mm: float) -> dict:
    """Plano de referencia paralelo a `base` (frontal/superior/lateral/nombre) a distancia_mm
    (el signo indica el lado, según la normal +Z/+Y/+X del plano base)."""
    return await _en_com(lambda: _con_arbol({"plano": s.plano_desfasado(base, distancia_mm)}))


@mcp.tool()
async def sw_eje(plano1: str, plano2: str) -> dict:
    """Eje de referencia en la intersección de dos planos.
    frontal + lateral = eje Y; frontal + superior = eje X; superior + lateral = eje Z."""
    return await _en_com(lambda: _con_arbol({"eje": s.eje(plano1, plano2)}))


@mcp.tool()
async def sw_patron_circular(operaciones: list[str], eje: str, cantidad: int,
                             angulo_total: float = 360) -> dict:
    """Repite operaciones alrededor de un eje de referencia, igualmente espaciadas."""
    return await _en_com(lambda: _con_arbol(
        {"operacion": s.patron_circular(operaciones, eje, cantidad, angulo_total)}))


@mcp.tool()
async def sw_cota(nombre: str, valor_mm: float | None = None) -> float:
    """Lee (o cambia, si das valor_mm) una cota como 'D1@Sketch1' o 'D1@Boss-Extrude1'. Reconstruye."""
    return await _en_com(lambda: s.cota(nombre, valor_mm))


@mcp.tool()
async def sw_editar(accion: str, operacion: str | None = None, pasos: int = 1) -> dict:
    """accion: 'deshacer' (pasos), 'borrar', 'suprimir' o 'activar' (des-suprimir) una operación."""
    def f():
        if accion == "deshacer":
            s.deshacer(pasos)
        elif accion == "borrar":
            s.borrar(operacion)
        elif accion in ("suprimir", "activar"):
            s.suprimir(operacion, accion == "suprimir")
        else:
            raise ValueError("accion debe ser deshacer, borrar, suprimir o activar")
        return _con_arbol({"ok": True})
    return await _en_com(f)


# ------------------------------------------------------------------ material, masa, vista
@mcp.tool()
async def sw_materiales(buscar: str = "") -> list[str]:
    """Busca en la biblioteca de materiales de SolidWorks (nombres en español, p. ej. 'ABS',
    'Nailon', 'Aluminio', 'PEEK'). Devuelve 'clase / material'."""
    return [f"{c} / {es}" + (f" (API: {en})" if en != es else "")
            for c, es, en in s.materiales(buscar)][:60]


@mcp.tool()
async def sw_material(nombre: str) -> str:
    """Asigna un material a la pieza activa (nombre exacto de sw_materiales)."""
    return await _en_com(lambda: s.material(nombre))


@mcp.tool()
async def sw_masa() -> dict:
    """Masa (g), volumen (cm³), área (cm²), centro de masa (mm), densidad y caja envolvente (mm)."""
    return await _en_com(s.masa)


@mcp.tool()
async def sw_ver(vista: str = "isometrica", ancho: int = 900, alto: int = 650) -> Image:
    """Captura la vista del documento activo para revisarlo. vista: isometrica, frontal, superior,
    derecha, izquierda, posterior, inferior, trimetrica, dimetrica, o 'actual' (sin mover la cámara)."""
    def f():
        if vista == "actual":
            return s.captura("", ancho, alto, ajustar=False)
        return s.captura(vista, ancho, alto)
    return Image(data=await _en_com(f), format="png")


# ------------------------------------------------------------------ ensamble
@mcp.tool()
async def sw_insertar_componente(ruta: str, x_mm: float = 0, y_mm: float = 0, z_mm: float = 0) -> dict:
    """Inserta una pieza o subensamble guardado en el ensamble activo, en la posición dada."""
    return await _en_com(lambda: _con_arbol({"componente": s.insertar_componente(ruta, x_mm, y_mm, z_mm)}))


# ------------------------------------------------------------------ escape hatch
_globales: dict[str, Any] = {}


@mcp.tool()
async def sw_python(codigo: str) -> str:
    """Ejecuta Python dentro del hilo COM con la API completa de SolidWorks 2020.

    Disponible: sw (ISldWorks), s (librería swlib), doc() (IModelDoc2 activo), K (constantes
    swconst), cast(obj, 'IInterfaz'), tipar(obj), arr(lista) (arreglo de dobles), MM=0.001, DEG.
    La API usa METROS y RADIANES. Asigna a `resultado` lo que quieras devolver; print también sale.
    Las variables persisten entre llamadas.
    """
    def f():
        g = _globales
        g.update(sw=s.conectar(), s=s, doc=s.doc, K=s.K, cast=s.cast, tipar=s.tipar,
                 arr=s.arr, MM=s.MM, DEG=s.DEG)
        g.pop("resultado", None)
        salida = io.StringIO()
        try:
            with contextlib.redirect_stdout(salida):
                exec(compile(codigo, "<sw_python>", "exec"), g)
        except Exception:
            return salida.getvalue() + "\n" + traceback.format_exc(limit=4)
        texto = salida.getvalue()
        if "resultado" in g:
            texto += ("\n" if texto else "") + f"resultado = {g['resultado']!r}"
        return texto or "(sin salida)"
    return await _en_com(f)


if __name__ == "__main__":
    mcp.run("stdio")
