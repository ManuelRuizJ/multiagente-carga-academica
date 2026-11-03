# -*- coding: utf-8 -*-
"""Uso:  python main.py --escenarios            (corre E1, E2, E3 con los datos de ejemplo)
        python main.py --matricula E1 --mensaje "quiero clases por la tarde" [--llm]
        python main.py --crewai --matricula E1  (orquestación con CrewAI + Ollama; ver README)"""
import argparse, csv, json, time
from pathlib import Path
from mas.kb import KB, RAIZ
from mas.preferencias import interpretar
from mas.scoring import Contexto, puntuar
from mas.coordinacion import contract_net
from mas.shapley import funcion_caracteristica, shapley
from mas.trazas import TraceCollector

NOMBRES = {"A": "Historial", "B": "Carga", "C": "Horarios"}

def correr(kb, matricula, mensaje=None, usar_llm=False):
    t0 = time.perf_counter(); traza = TraceCollector()
    e = kb.datos["estudiantes"]; msg = mensaje or next(x["mensaje"] for x in e if x["matricula"] == matricula)
    t = time.perf_counter(); prefs, fuente = interpretar(msg, usar_llm)
    traza.registrar("AgenteHorarios", "interpretar_preferencias", msg, prefs, t, True)
    t = time.perf_counter(); cur = kb.cursables(matricula)
    traza.registrar("AgenteHistorial", "verificar_prerrequisitos", matricula, [c for c, (ok, _) in cur.items() if ok], t)
    cmin, cmax = kb.limites_creditos()
    ctx = Contexto(matricula, cur, kb.grupos_periodo(), prefs, cmin, cmax)
    res = contract_net(ctx, traza)
    t = time.perf_counter(); v = funcion_caracteristica(ctx); phi = shapley(v)
    traza.registrar("TraceCollector", "calcular_shapley", "8 coaliciones", {NOMBRES[k]: round(x, 2) for k, x in phi.items()}, t)
    if res['estado'] == 'exito': kb.registrar_recomendacion(matricula, res, ctx, {NOMBRES[k]: x for k, x in phi.items()}, traza, v)
    return dict(matricula=matricula, mensaje=msg, preferencias=prefs, fuente_prefs=fuente, cursables=[c for c, (ok, _) in cur.items() if ok],
                resultado=res, v={"".join(sorted(k)) or "∅": round(x, 2) for k, x in v.items()}, shapley={NOMBRES[k]: round(x, 2) for k, x in phi.items()},
                tiempo_total=round(time.perf_counter() - t0, 2)), traza, ctx

def mostrar(r, ctx):
    print(f"\n=== {r['matricula']} ===\nMensaje: {r['mensaje']}\nPreferencias ({r['fuente_prefs']}): {r['preferencias']}\nCursables: {r['cursables']}")
    for p in r["resultado"]["propuestas"]:
        print(f"  {p['autor']:<28} Score={p['Score']:5.1f} Av={p['Av']:5.1f} Ho={p['Ho']:5.1f} Ca={p['Ca']:5.1f} Pr={p['Pr']:5.1f} "
              f"cred={p['creditos']:>2} choques={p['conflictos']} inválidas={p['invalidas']} {p['grupos']}")
    m = r["resultado"].get("mejor")
    if m: print("  >> RECOMENDACIÓN:", ", ".join(f"{g} ({ctx.grupos[g]['nombre']})" for g in m["grupos"]), f"| {m['creditos']} créditos | Score {m['Score']:.1f}")
    print("  Shapley:", r["shapley"], "| v(N) =", r["v"]["ABC"])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--escenarios", action="store_true"); ap.add_argument("--matricula"); ap.add_argument("--mensaje")
    ap.add_argument("--llm", action="store_true"); ap.add_argument("--crewai", action="store_true"); a = ap.parse_args()
    kb = KB()
    if a.crewai:
        from mas.crew_mas import ejecutar_crew; print(ejecutar_crew(kb, a.matricula or "E1", a.mensaje)); raise SystemExit
    mats = [x["matricula"] for x in kb.datos["estudiantes"]] if a.escenarios else [a.matricula or "E1"]
    out = []
    for m in mats:
        r, traza, ctx = correr(kb, m, a.mensaje if not a.escenarios else None, a.llm); mostrar(r, ctx); out.append(r)
        traza.guardar(RAIZ / "resultados" / f"trazas_{m}.json")
    (RAIZ / "resultados" / "resultados.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
    with open(RAIZ / "resultados" / "tabla1.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["Escenario", "Materias", "Creditos", "Conflictos", "Score", "Tiempo_s"])
        for r in out:
            mj = r["resultado"].get("mejor")
            if mj: w.writerow([r["matricula"], " ".join(mj["grupos"]), mj["creditos"], mj["conflictos"], round(mj["Score"], 1), r["tiempo_total"]])
    kb.guardar(RAIZ / "resultados" / "ontologia_poblada.owl")
    print("\nResultados guardados en resultados/ (incluye ontologia_poblada.owl para abrir en Protégé)")
