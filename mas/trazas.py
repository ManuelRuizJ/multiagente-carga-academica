# -*- coding: utf-8 -*-
"""Trace Collector: registra cada acción de los agentes (insumo para Shapley y auditoría)."""
import json, time
from datetime import datetime

class TraceCollector:
    def __init__(self): self.eventos = []
    def registrar(self, agente, tarea, entrada, salida, t_ini, exito=True, score=None):
        self.eventos.append(dict(timestamp=datetime.now().isoformat(timespec="seconds"), agent=agente, task=tarea,
                                 input=entrada, output=salida, execution_time=round(time.perf_counter() - t_ini, 4),
                                 success=exito, score=None if score is None else round(score, 2)))
    def guardar(self, ruta):
        with open(ruta, "w", encoding="utf-8") as f: json.dump(self.eventos, f, ensure_ascii=False, indent=1)
