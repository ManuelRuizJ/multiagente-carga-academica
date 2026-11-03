# -*- coding: utf-8 -*-
"""Agentes especializados (lógica determinista) y coordinación Contract Net en Python puro."""
import time
from .scoring import puntuar, PESOS

AGENTES = {"A": "AgenteHistorial", "B": "AgenteCarga", "C": "AgenteHorarios"}
MAX_MATERIAS = 6

def mejor_propuesta(coalicion, ctx):
    """Mejor carga que puede construir una coalición de agentes.
    A (historial) impone validez de seriación y optimiza avance; B (carga) impone límites de créditos y optimiza equilibrio;
    C (horarios) impone ausencia de choques y optimiza horario + preferencias. Un agente ausente no impone ni optimiza nada."""
    if not coalicion: return []
    gpm = {}
    for cl, g in sorted(ctx.grupos.items()):
        if "A" in coalicion and not ctx.cursables[g["materia"]][0]: continue
        gpm.setdefault(g["materia"], []).append(cl)
    mats = sorted(gpm); mejor = {"obj": -1, "cr": -1, "combo": []}
    def obj(c):
        s = 0
        if "A" in coalicion: s += PESOS["Av"] * c["Av"]
        if "B" in coalicion: s += PESOS["Ca"] * c["Ca"]
        if "C" in coalicion: s += PESOS["Ho"] * c["Ho"] + PESOS["Pr"] * c["Pr"]
        return s
    def dfs(i, combo, tot):
        if combo:
            if not ("B" in coalicion and not (ctx.cmin <= tot <= ctx.cmax)):
                c = puntuar(combo, ctx); o = obj(c)
                if (o, tot) > (mejor["obj"], mejor["cr"]): mejor.update(obj=o, cr=tot, combo=list(combo))
        if i == len(mats) or len(combo) == MAX_MATERIAS: return
        for j in range(i, len(mats)):
            for g in gpm[mats[j]]:
                cr = ctx.grupos[g]["creditos"]
                if "B" in coalicion and tot + cr > ctx.cmax: continue
                if "C" in coalicion and any(ctx.conflictos[(g, x)] for x in combo): continue
                combo.append(g); dfs(j + 1, combo, tot + cr); combo.pop()
    dfs(0, [], 0)
    return mejor["combo"]

def contract_net(ctx, traza):
    """1) El Manager solicita propuestas; 2) cada agente propone desde su especialidad; 3) el Manager integra las restricciones
    de los tres y 4) selecciona la propuesta de mayor Score (ecuación 1)."""
    t0 = time.perf_counter()
    solicitud = dict(estudiante=ctx.matricula, preferencias=ctx.prefs, creditos=(ctx.cmin, ctx.cmax))
    propuestas = []
    for k, nombre in AGENTES.items():
        t = time.perf_counter(); combo = mejor_propuesta({k}, ctx); sc = puntuar(combo, ctx)
        traza.registrar(nombre, "proponer_carga", solicitud, combo, t, True, sc["Score"])
        propuestas.append(dict(autor=nombre, grupos=combo, **sc))
    t = time.perf_counter(); combo = mejor_propuesta({"A", "B", "C"}, ctx); sc = puntuar(combo, ctx)
    traza.registrar("AgenteManager", "integrar_propuestas", [p["autor"] for p in propuestas], combo, t, bool(combo), sc["Score"])
    propuestas.append(dict(autor="AgenteManager (integrada)", grupos=combo, **sc))
    if not any(p["grupos"] for p in propuestas): return dict(estado="sin_propuesta", propuestas=propuestas)
    best = max(propuestas, key=lambda p: p["Score"])
    traza.registrar("AgenteManager", "seleccionar_mejor", [p["autor"] for p in propuestas], best["autor"], t0, True, best["Score"])
    return dict(estado="exito", mejor=best, propuestas=propuestas)
