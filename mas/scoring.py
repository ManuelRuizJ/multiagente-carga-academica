# -*- coding: utf-8 -*-
"""Función de evaluación (ecuación 1 del reporte): Score = 0.30*Av + 0.25*Ho + 0.25*Ca + 0.20*Pr"""
from dataclasses import dataclass, field
PESOS = dict(Av=0.30, Ho=0.25, Ca=0.25, Pr=0.20)
PESO_TIPO = {"MateriaObligatoria": 1.0, "MateriaOptativa": 0.6, "MateriaElectiva": 0.4}
OBJETIVO = {"ligera": 0.15, "normal": 0.5, "pesada": 0.9}     # posición dentro de [min, max] de créditos

@dataclass
class Contexto:
    matricula: str
    cursables: dict          # clave materia -> (bool, faltantes)
    grupos: dict             # clave grupo -> info
    prefs: dict              # turno / modalidad / carga
    cmin: int
    cmax: int
    conflictos: dict = field(default_factory=dict)   # (g1,g2) -> bool

    def __post_init__(self):
        ks = sorted(self.grupos)
        for i, a in enumerate(ks):
            for b in ks[i + 1:]: self.conflictos[(a, b)] = self.conflictos[(b, a)] = choque(self.grupos[a], self.grupos[b])
    @property
    def objetivo_creditos(self):
        return self.cmin + OBJETIVO.get(self.prefs.get("carga") or "normal") * (self.cmax - self.cmin)

def choque(g1, g2):
    return any(d1 == d2 and i1 < f2 and i2 < f1 for d1, i1, f1, _ in g1["bloques"] for d2, i2, f2, _ in g2["bloques"])

def componentes(combo, ctx):
    gs = [ctx.grupos[c] for c in combo]; tot = sum(g["creditos"] for g in gs)
    if not gs: return dict(Av=0, Ho=0, Ca=0, Pr=0, creditos=0, conflictos=0, invalidas=0)
    inval = sum(1 for g in gs if not ctx.cursables[g["materia"]][0])
    Av = 100 * sum(g["creditos"] * PESO_TIPO[g["tipo"]] * ctx.cursables[g["materia"]][0] for g in gs) / tot
    nconf = sum(1 for i, a in enumerate(combo) for b in combo[i + 1:] if ctx.conflictos[(a, b)])
    Ho = max(0, 100 - 50 * nconf)
    tgt = ctx.objetivo_creditos
    Ca = 0 if not (ctx.cmin <= tot <= ctx.cmax) else 100 * max(0, 1 - abs(tot - tgt) / tgt)
    chk = []
    if ctx.prefs.get("turno"): chk.append(sum(all(b[3] == ctx.prefs["turno"] for b in g["bloques"]) for g in gs) / len(gs))
    if ctx.prefs.get("modalidad"): chk.append(sum(g["modalidad"] == ctx.prefs["modalidad"] for g in gs) / len(gs))
    Pr = 100 * sum(chk) / len(chk) if chk else 100
    return dict(Av=Av, Ho=Ho, Ca=Ca, Pr=Pr, creditos=tot, conflictos=nconf, invalidas=inval)

def puntuar(combo, ctx):
    c = componentes(combo, ctx)
    c["Score"] = sum(PESOS[k] * c[k] for k in PESOS)
    return c
