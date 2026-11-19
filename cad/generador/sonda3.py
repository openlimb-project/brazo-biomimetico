"""Averiguar el sentido real de FeatureCut4 / FeatureExtrusion3 (parámetros Flip y Dir)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swx
from swx import s

MM = 0.001


def bloque():
    md = s.nuevo("pieza")
    sk = s.croquis([{"tipo": "rectangulo", "x": 0, "y": 0, "ancho": 20, "alto": 20}], "frontal", md=md)
    s.extruir(sk, 20, md=md)                      # z 0..20 si va hacia +Z
    return md


def corte(md, flip, direc):
    pl = s.plano_desfasado("frontal", 10, md=md)
    sk = s.croquis([{"tipo": "circulo", "x": 0, "y": 0, "r": 5}], pl, md=md)
    s._seleccionar_croquis(sk, md)
    K = s.K
    f = md.FeatureManager.FeatureCut4(True, flip, direc, K.swEndCondBlind, K.swEndCondBlind, 5 * MM, 0,
                                      False, False, False, False, 0, 0, False, False, False, False,
                                      False, True, True, True, True, False, 0, 0, False, False)
    return f is not None


def saliente(md, flip, direc):
    pl = s.plano_desfasado("frontal", 30, md=md)
    sk = s.croquis([{"tipo": "circulo", "x": 0, "y": 0, "r": 5}], pl, md=md)
    s._seleccionar_croquis(sk, md)
    K = s.K
    f = md.FeatureManager.FeatureExtrusion3(True, flip, direc, K.swEndCondBlind, K.swEndCondBlind, 5 * MM, 0,
                                            False, False, False, False, 0, 0, False, False, False, False,
                                            False, True, True, 0, 0, False)
    return f is not None


swx.iniciar()
md = bloque()
print("bloque:", s.masa(md)["caja_mm_xyz"], swx.caja_pieza(md), "cdm", s.masa(md)["centro_masa_mm"])
for flip, direc in ((False, False), (False, True), (True, False)):
    md = bloque()
    ok = corte(md, flip, direc)
    m = s.masa(md)
    print(f"corte flip={flip} dir={direc}: ok={ok} vol={m['volumen_cm3']} cdm_z={m['centro_masa_mm'][2]}")
for flip, direc in ((False, False), (False, True), (True, False)):
    md = bloque()
    ok = saliente(md, flip, direc)
    print(f"saliente flip={flip} dir={direc}: ok={ok} caja={swx.caja_pieza(md)}")
