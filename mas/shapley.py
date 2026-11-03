# -*- coding: utf-8 -*-
"""Valores de Shapley exactos para los 3 agentes especializados: v(S) = Score de la mejor propuesta de la coalición S."""
from itertools import combinations
from math import factorial
from .coordinacion import mejor_propuesta
from .scoring import puntuar

def funcion_caracteristica(ctx):
    v = {}
    for r in range(4):
        for S in combinations("ABC", r):
            combo = mejor_propuesta(set(S), ctx)
            v[frozenset(S)] = puntuar(combo, ctx)["Score"] if combo else 0.0
    return v

def shapley(v, jugadores="ABC"):
    n = len(jugadores); phi = {}
    for i in jugadores:
        otros = [j for j in jugadores if j != i]; tot = 0.0
        for r in range(len(otros) + 1):
            for S in combinations(otros, r):
                S = frozenset(S); w = factorial(len(S)) * factorial(n - len(S) - 1) / factorial(n)
                tot += w * (v[S | {i}] - v[S])
        phi[i] = tot
    return phi
