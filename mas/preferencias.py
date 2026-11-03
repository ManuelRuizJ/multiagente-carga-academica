# -*- coding: utf-8 -*-
"""Interpretación de preferencias en lenguaje natural. LLM (Ollama) con validación estricta + respaldo por reglas."""
import json, os, re

MODELO = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

TURNOS, MODS, CARGAS = {"matutino", "vespertino"}, {"presencial", "enlinea", "hibrida"}, {"ligera", "normal", "pesada"}

def por_reglas(texto):
    t = texto.lower(); p = {"turno": None, "modalidad": None, "carga": None}
    if re.search(r"tarde|vespertin", t): p["turno"] = "vespertino"
    elif re.search(r"mañana|manana|matutin|temprano", t): p["turno"] = "matutino"
    if re.search(r"en l[ií]nea|online|remot|a distancia", t): p["modalidad"] = "enlinea"
    elif re.search(r"presencial", t): p["modalidad"] = "presencial"
    elif re.search(r"h[ií]brid", t): p["modalidad"] = "hibrida"
    if re.search(r"ligera|poca carga|pocas materias|tranquil|menos materias", t): p["carga"] = "ligera"
    elif re.search(r"pesada|m[aá]xima|muchas materias|cargad", t): p["carga"] = "pesada"
    elif re.search(r"normal|est[aá]ndar", t): p["carga"] = "normal"
    return p

def validar(d):
    """El LLM NUNCA define valores fuera del vocabulario de la ontología: lo que no sea válido se descarta."""
    return {"turno": d.get("turno") if d.get("turno") in TURNOS else None,
            "modalidad": d.get("modalidad") if d.get("modalidad") in MODS else None,
            "carga": d.get("carga") if d.get("carga") in CARGAS else None}

def por_llm(texto, modelo=MODELO, url=URL):
    import requests
    prompt = ('Extrae preferencias de horario de un estudiante. Responde SOLO un JSON con las claves "turno" '
              '(matutino|vespertino|null), "modalidad" (presencial|enlinea|hibrida|null) y "carga" (ligera|normal|pesada|null).\n'
              f'Mensaje: "{texto}"')
    r = requests.post(f"{url}/api/chat", json={"model": modelo, "stream": False, "format": "json", "options": {"temperature": 0},
                                              "messages": [{"role": "user", "content": prompt}]}, timeout=120)
    data = r.json()
    if "message" not in data:                       # Ollama devolvió un error (p. ej. caída del backend de GPU)
        raise RuntimeError(str(data.get("error", data))[:300])
    return validar(json.loads(data["message"]["content"]))

def interpretar(texto, usar_llm=False, **kw):
    """Devuelve (preferencias, fuente)."""
    if usar_llm:
        try: return por_llm(texto, **kw), "llm"
        except Exception as e: print(f"[aviso] Ollama falló -> {type(e).__name__}: {e}\n        Se usan reglas. (Revisa que Ollama corra en CPU: ver README, sección ROCm.)")
    return por_reglas(texto), "reglas"
