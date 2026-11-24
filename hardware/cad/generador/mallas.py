"""Convierte los STL de cad/brazo_v0/stl en un solo archivo de mallas para el visor web.

Para cada pieza suelda los vértices, calcula normales suaves respetando las aristas vivas
(ángulo de pliegue) y guarda posiciones (float32), normales (int8) e índices en base64.
Copia además modelo.json a software/simulador/modelo3d/.
"""
import base64
import json
import math
import os
import shutil
import struct
import sys
from array import array

AQUI = os.path.dirname(os.path.abspath(__file__))
ORIGEN = os.path.abspath(os.path.join(AQUI, "..", "brazo_v0"))
DESTINO = os.path.abspath(os.path.join(AQUI, "..", "..", "..", "software", "simulador", "modelo3d"))
PLIEGUE = math.cos(math.radians(38))


def leer_stl(ruta):
    with open(ruta, "rb") as f:
        datos = f.read()
    n = struct.unpack_from("<I", datos, 80)[0]
    if 84 + 50 * n != len(datos):
        raise ValueError(f"{ruta}: no es un STL binario")
    tris = []
    for i in range(n):
        v = struct.unpack_from("<12f", datos, 84 + 50 * i)
        tris.append((v[3:6], v[6:9], v[9:12]))
    return tris


def normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)      # módulo = 2 x área


def malla(tris):
    clave = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
    caras = []
    por_vertice = {}
    for t in tris:
        nx, ny, nz = normal(*t)
        m = math.sqrt(nx * nx + ny * ny + nz * nz)
        if m < 1e-12:
            continue
        idx = len(caras)
        caras.append((t, (nx, ny, nz), (nx / m, ny / m, nz / m)))
        for p in t:
            por_vertice.setdefault(clave(p), []).append(idx)
    pos, nor, ind, vistos = array("f"), array("b"), [], {}
    for idx, (t, _, nu) in enumerate(caras):
        for p in t:
            sx = sy = sz = 0.0
            for j in por_vertice[clave(p)]:
                nj, uj = caras[j][1], caras[j][2]
                if nu[0] * uj[0] + nu[1] * uj[1] + nu[2] * uj[2] >= PLIEGUE:
                    sx += nj[0]; sy += nj[1]; sz += nj[2]
            m = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
            q = (int(round(127 * sx / m)), int(round(127 * sy / m)), int(round(127 * sz / m)))
            k = (clave(p), q)
            i = vistos.get(k)
            if i is None:
                i = vistos[k] = len(vistos)
                pos.extend(p)
                nor.extend(q)
            ind.append(i)
    i16 = len(vistos) < 65536
    idx_arr = array("H" if i16 else "I", ind)
    b = lambda a: base64.b64encode(a.tobytes()).decode("ascii")
    return {"p": b(pos), "n": b(nor), "i": b(idx_arr), "i16": i16, "nv": len(vistos), "nt": len(caras)}


def main():
    os.makedirs(DESTINO, exist_ok=True)
    salida, total_t, total_v = {}, 0, 0
    carpeta = os.path.join(ORIGEN, "stl")
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.lower().endswith(".stl"):
            continue
        m = malla(leer_stl(os.path.join(carpeta, nombre)))
        salida[os.path.splitext(nombre)[0]] = m
        total_t += m["nt"]; total_v += m["nv"]
        print(f"  {nombre}: {m['nt']} triángulos, {m['nv']} vértices")
    ruta = os.path.join(DESTINO, "mallas.json")
    json.dump(salida, open(ruta, "w", encoding="ascii"), separators=(",", ":"))
    shutil.copyfile(os.path.join(ORIGEN, "modelo.json"), os.path.join(DESTINO, "modelo.json"))
    print(f"mallas.json: {os.path.getsize(ruta) / 1e6:.2f} MB, {total_t} triángulos, {total_v} vértices, {len(salida)} piezas")


if __name__ == "__main__":
    sys.exit(main())
