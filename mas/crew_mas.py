# -*- coding: utf-8 -*-
"""Capa de orquestación con CrewAI (Process.hierarchical) + Ollama. Las herramientas llaman a la lógica en Python puro y a la ontología."""
import json, os
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from .preferencias import interpretar
from .scoring import Contexto, puntuar
from .coordinacion import contract_net
from .trazas import TraceCollector

E = {}   # estado compartido de la ejecución (kb, contexto, trazas)

def _ctx():
    return E["ctx"]

def _mat(arg=""):
    """La matrícula SIEMPRE es la del alumno en curso. Si el LLM manda otra (p. ej. '12345'), se ignora."""
    return E["matricula"]

def _seguro(f):
    """Una herramienta nunca debe lanzar excepciones: devuelve un JSON de error con instrucciones claras para el agente."""
    import functools
    @functools.wraps(f)
    def g(*a, **k):
        try: return f(*a, **k)
        except Exception as ex:
            return json.dumps({"error": f"{type(ex).__name__}: {ex}", "ayuda": f"La matrícula correcta es {E['matricula']}. No inventes valores; "
                               "usa solo los que te dieron en la tarea."}, ensure_ascii=False)
    return g

@tool("consultar_historial")
@_seguro
def consultar_historial(matricula: str = "") -> str:
    """Devuelve el historial académico (materia -> aprobado/reprobado/en_curso) del estudiante en curso, leído de la ontología. El parámetro matricula se ignora."""
    return json.dumps(E["kb"].historial(_mat(matricula)), ensure_ascii=False)

@tool("verificar_prerrequisitos")
@_seguro
def verificar_prerrequisitos(matricula: str = "") -> str:
    """Devuelve qué materias puede cursar el estudiante en curso (cumple seriación) y qué prerrequisitos le faltan en las demás. El parámetro matricula se ignora."""
    return json.dumps({c: {"puede": ok, "faltan": f} for c, (ok, f) in E["kb"].cursables(_mat(matricula)).items()}, ensure_ascii=False)

@tool("consultar_horarios")
@_seguro
def consultar_horarios(dummy: str = "") -> str:
    """Lista los grupos ofertados del periodo con materia, créditos, modalidad y bloques horarios."""
    return json.dumps({k: {x: g[x] for x in ("materia", "creditos", "modalidad", "bloques")} for k, g in _ctx().grupos.items()}, ensure_ascii=False)

@tool("calcular_creditos")
@_seguro
def calcular_creditos(claves_grupo: str) -> str:
    """Suma los créditos de una lista de grupos separados por coma (ej. 'RED301-A,SO301-B')."""
    gs = [x.strip() for x in claves_grupo.split(",") if x.strip()]
    return json.dumps({"creditos": sum(_ctx().grupos[g]["creditos"] for g in gs), "materias": len(gs)})

@tool("detectar_conflictos")
@_seguro
def detectar_conflictos(claves_grupo: str) -> str:
    """Detecta choques de horario entre los grupos indicados (separados por coma)."""
    gs = [x.strip() for x in claves_grupo.split(",") if x.strip()]
    c = _ctx(); return json.dumps({"choques": [[a, b] for i, a in enumerate(gs) for b in gs[i + 1:] if c.conflictos[(a, b)]]})

@tool("evaluar_carga")
@_seguro
def evaluar_carga(claves_grupo: str) -> str:
    """Evalúa una propuesta (avance, horario, carga, preferencias y Score total) para los grupos indicados."""
    gs = [x.strip() for x in claves_grupo.split(",") if x.strip()]
    return json.dumps({k: round(v, 1) for k, v in puntuar(gs, _ctx()).items()})

@tool("interpretar_preferencias")
@_seguro
def interpretar_preferencias(texto: str) -> str:
    """Convierte el mensaje del alumno en preferencias estructuradas (turno, modalidad, carga) validadas contra el vocabulario de la ontología."""
    p, f = interpretar(texto, usar_llm=False); return json.dumps({"preferencias": p, "fuente": f})

@tool("coordinar_carga")
@_seguro
def coordinar_carga(matricula: str = "") -> str:
    """Ejecuta el protocolo Contract Net (en Python puro) para el estudiante en curso: solicita propuestas a los tres agentes, las integra, las evalúa y devuelve la mejor. El parámetro matricula se ignora."""
    res = contract_net(_ctx(), E["traza"]); E["resultado"] = res
    if res["estado"] != "exito": return json.dumps({"estado": res["estado"]})
    m = res["mejor"]; return json.dumps({"estado": "exito", "grupos": m["grupos"], "creditos": m["creditos"], "Score": round(m["Score"], 1),
                                         "Av": round(m["Av"], 1), "Ho": round(m["Ho"], 1), "Ca": round(m["Ca"], 1), "Pr": round(m["Pr"], 1)})

def construir_crew(llm, verbose=True):
    hist = Agent(role="Analista de historial académico y requisitos", goal="Determinar qué materias puede cursar el estudiante según su historial, prerrequisitos y seriación.",
                 backstory="Analiza la trayectoria del alumno (aprobadas, reprobadas, pendientes) y descarta las materias que aún no puede cursar.",
                 tools=[consultar_historial, verificar_prerrequisitos, coordinar_carga], llm=llm, verbose=verbose, allow_delegation=False, max_iter=4, max_execution_time=600)
    carga = Agent(role="Analista de carga académica", goal="Evaluar combinaciones de materias y determinar cuáles representan una carga equilibrada.",
                  backstory="Analiza créditos y número de materias para evitar cargas excesivas respetando los límites institucionales.",
                  tools=[calcular_creditos, evaluar_carga, coordinar_carga], llm=llm, verbose=verbose, allow_delegation=False, max_iter=4, max_execution_time=600)
    hor = Agent(role="Analista de horarios y preferencias", goal="Evaluar compatibilidad de horarios y adaptar las propuestas a las preferencias del alumno.",
                backstory="Interpreta preferencias cualitativas (carga ligera, tarde, en línea) y detecta choques de horario.",
                tools=[consultar_horarios, detectar_conflictos, interpretar_preferencias, coordinar_carga], llm=llm, verbose=verbose, allow_delegation=False, max_iter=4, max_execution_time=600)
    manager = Agent(role="Coordinador y recomendador académico", goal="Coordinar a los especialistas, comparar sus propuestas y entregar la mejor carga académica.",
                    backstory="Evolución del agente asesor original: integra los resultados de historial, carga y horarios y genera la recomendación final.",
                    llm=llm, verbose=verbose, allow_delegation=True, max_iter=6, max_execution_time=900)     # CrewAI no permite herramientas en el manager jerárquico
    t1 = Task(description="IMPORTANTE: la matrícula del estudiante es EXACTAMENTE '{matricula}' (no inventes otra). Consulta su historial y verifica prerrequisitos: lista las materias que puede cursar.",
              expected_output="Lista de materias cursables y las que no puede cursar con el motivo.", agent=hist)
    t2 = Task(description="IMPORTANTE: la matrícula es '{matricula}'. Analiza la carga posible en créditos y número de materias.",
              expected_output="Rango de créditos recomendable y criterios de equilibrio.", agent=carga)
    t3 = Task(description="IMPORTANTE: usa solo la información dada. Interpreta las preferencias del alumno: '{mensaje}' y evalúa conflictos de horario de la oferta.",
              expected_output="Preferencias estructuradas y restricciones de horario.", agent=hor)
    t4 = Task(description="Con los resultados anteriores, ejecuta UNA SOLA VEZ la herramienta coordinar_carga (matrícula '{matricula}') y redacta la recomendación final con materias, grupos, créditos y justificación.",
              expected_output="Recomendación final de carga académica con justificación.")
    return Crew(agents=[hist, carga, hor], tasks=[t1, t2, t3, t4], process=Process.hierarchical, manager_agent=manager, verbose=verbose, max_rpm=None)

def verificar_ollama(modelo, url):
    """Prueba mínima (1 token) antes de lanzar el crew. Devuelve (ok, mensaje)."""
    import requests
    try:
        r = requests.post(f"{url}/api/generate", json={"model": modelo, "prompt": "ok", "stream": False, "options": {"num_predict": 1}}, timeout=300)
        d = r.json()
        return ("error" not in d), str(d.get("error", "ok"))[:250]
    except Exception as ex:
        return False, f"{type(ex).__name__}: {ex}"

def ejecutar_crew(kb, matricula, mensaje=None, modelo=None, url=None):
    modelo = modelo or "ollama/" + os.getenv("OLLAMA_MODEL", "llama3.1:8b"); url = url or os.getenv("OLLAMA_URL", "http://localhost:11434")
    if matricula not in kb.estudiantes: raise ValueError(f"Matrícula desconocida: {matricula}. Opciones: {list(kb.estudiantes)}")
    msg = mensaje or next(x["mensaje"] for x in kb.datos["estudiantes"] if x["matricula"] == matricula)
    prefs, _ = interpretar(msg)
    cur = kb.cursables(matricula); cmin, cmax = kb.limites_creditos()
    E.clear(); E.update(kb=kb, matricula=matricula, traza=TraceCollector(), ctx=Contexto(matricula, cur, kb.grupos_periodo(), prefs, cmin, cmax))
    llm = LLM(model=modelo, base_url=url, temperature=0)
    texto, origen = None, "crewai"
    ok, info = verificar_ollama(modelo.replace("ollama/", ""), url)
    if not ok:
        print(f"[aviso] Ollama no responde -> {info}\n        No se lanza el crew; se usa el respaldo determinista.")
        origen = "respaldo determinista (Ollama caído)"
    else:
      try:
        texto = str(construir_crew(llm).kickoff(inputs={"matricula": matricula, "mensaje": msg}))
      except BaseException as ex:                                   # incluye KeyboardInterrupt (Ctrl+C si el LLM se atora)
        origen = f"respaldo determinista ({type(ex).__name__})"
    if "resultado" not in E:                                      # el LLM nunca llegó a coordinar_carga: se ejecuta Contract Net directamente
        E["resultado"] = contract_net(E["ctx"], E["traza"]); origen += " + Contract Net directo"
    res = E["resultado"]; m = res.get("mejor")
    resumen = "Sin propuesta válida." if not m else (f"Recomendación ({origen}): " + ", ".join(m["grupos"]) +
              f" | {m['creditos']} créditos | Score {m['Score']:.1f}")
    return (texto + "\n\n" if texto else "") + resumen
