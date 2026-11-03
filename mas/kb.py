# -*- coding: utf-8 -*-
"""Base de conocimiento: carga la ontología OWL (P2_ontologia_carga_academica.owx) y la puebla con datos.
La ontología es la fuente de verdad: todo lo demás (herramientas, agentes) lee de aquí."""
import json
from pathlib import Path
from owlready2 import get_ontology, sync_reasoner_hermit

RAIZ = Path(__file__).resolve().parent.parent
MOD = {"presencial": "ModalidadPresencial", "enlinea": "ModalidadEnLinea", "hibrida": "ModalidadHibrida"}

class KB:
    def __init__(self, owx=RAIZ / "ontologia" / "P2_ontologia_carga_academica.owx", datos=RAIZ / "datos" / "catalogo_ejemplo.json"):
        self.o = get_ontology(Path(owx).as_uri()).load()
        self.datos = json.loads(Path(datos).read_text(encoding="utf-8"))
        self._poblar()

    # ------------------------------------------------------------ población
    def _poblar(self):
        o, d = self.o, self.datos
        with o:
            prog = o.ProgramaEducativo("prog_1"); prog.nombrePrograma = d["programa"]["nombre"]; prog.creditosTotales = d["programa"]["creditosTotales"]
            plan = o.PlanDeEstudios("plan_1"); plan.anioPlan = d["plan"]["anio"]; plan.calificacionMinimaAprobatoria = d["plan"]["calificacionMinimaAprobatoria"]
            prog.tienePlan.append(plan)
            rc = o.RestriccionDeCarga("restr_1"); rc.cargaMinimaCreditos = d["plan"]["cargaMinimaCreditos"]; rc.cargaMaximaCreditos = d["plan"]["cargaMaximaCreditos"]
            self.periodo = o.PeriodoEscolar("per_" + d["periodo"]["clave"]); self.periodo.clavePeriodo = d["periodo"]["clave"]
            self.restriccion = rc
            self.modalidades = {}
            for k, cls in MOD.items():
                x = getattr(o, cls)("mod_" + k); x.nombreModalidad = k; self.modalidades[k] = x
            prof = {}
            for p in d["profesores"]:
                x = o.Profesor("prof_" + p["clave"]); x.nombrePersona = p["nombre"]; x.claveEmpleado = p["clave"]; prof[p["clave"]] = x
            self.materias = {}
            for mt in d["materias"]:
                cls = {"obligatoria": o.MateriaObligatoria, "optativa": o.MateriaOptativa, "electiva": o.MateriaElectiva}[mt["tipo"]]
                x = cls("mat_" + mt["clave"]); x.claveMateria = mt["clave"]; x.nombreMateria = mt["nombre"]; x.creditos = mt["creditos"]
                sem = o.Semestre("sem_%d" % mt["semestre"]); sem.semestreSugerido = mt["semestre"]; x.ubicadaEnSemestre = sem
                x.perteneceAPlan = plan
                self.materias[mt["clave"]] = x
            for mt in d["materias"]:                      # seriación (después de crear todas)
                for p in mt["prereq"]: self.materias[mt["clave"]].tienePrerrequisito.append(self.materias[p])
            self.dificultad = {mt["clave"]: mt["dificultad"] for mt in d["materias"]}
            self.grupos = {}
            for g in d["grupos"]:
                x = o.Grupo("grp_" + g["clave"]); x.claveGrupo = g["clave"]; x.cupo = g["cupo"]
                x.ofreceMateria = self.materias[g["materia"]]; x.impartidoPor = prof[g["profesor"]]
                x.tieneModalidad = self.modalidades[g["modalidad"]]; x.seOfertaEnPeriodo = self.periodo
                for i, h in enumerate(g["horarios"]):
                    hh = o.Horario(f"hor_{g['clave']}_{i}"); hh.diaSemana = h["dia"]; hh.inicioMinutos = h["ini"]; hh.finMinutos = h["fin"]
                    hh.turno = "matutino" if h["ini"] < 14 * 60 else "vespertino"; x.tieneHorario.append(hh)
                self.grupos[g["clave"]] = x
            self.estudiantes = {}
            for e in d["estudiantes"]:
                x = o.Estudiante("est_" + e["matricula"]); x.matricula = e["matricula"]; x.nombrePersona = e["nombre"]; x.semestreActual = e["semestre"]
                x.cursaPrograma = prog
                for i, r in enumerate(e["kardex"]):
                    cls = {"aprobado": o.RegistroAprobado, "reprobado": o.RegistroReprobado, "en_curso": o.RegistroEnCurso}[r["estado"]]
                    rr = cls(f"reg_{e['matricula']}_{i}"); rr.numeroOportunidad = r["intento"]
                    if r["estado"] != "en_curso": rr.calificacion = float(r["calificacion"])
                    rr.registraMateria = self.materias[r["materia"]]; x.tieneRegistro.append(rr)
                self.estudiantes[e["matricula"]] = x

    # ------------------------------------------------------------ consultas (lo que usan las herramientas)
    def historial(self, matricula):
        """{clave: estado} leído de los RegistroAcademico del estudiante en la ontología."""
        e, o, h = self.estudiantes[matricula], self.o, {}
        for r in e.tieneRegistro:
            est = "aprobado" if isinstance(r, o.RegistroAprobado) else "reprobado" if isinstance(r, o.RegistroReprobado) else "en_curso"
            h[r.registraMateria.claveMateria] = est
        return h

    def cursables(self, matricula):
        """Verificación de prerrequisitos/seriación. Devuelve {clave: (puede, [faltantes])} y asserta puedeCursar/haAprobado en la ontología.
        Nota OWA: la ausencia de un RegistroAprobado se trata aquí como 'no acreditado' (cierre local explícito)."""
        h = self.historial(matricula); e = self.estudiantes[matricula]; res = {}
        for cl, m in self.materias.items():
            if h.get(cl) in ("aprobado", "en_curso"): res[cl] = (False, ["ya " + h[cl]]); continue
            falt = [p.claveMateria for p in m.tienePrerrequisito if h.get(p.claveMateria) != "aprobado"]
            res[cl] = (not falt, falt)
        with self.o:
            e.haAprobado = [self.materias[c] for c, s in h.items() if s == "aprobado"]
            e.puedeCursar = [self.materias[c] for c, (ok, _) in res.items() if ok]
        return res

    def grupos_periodo(self):
        out = {}
        for cl, g in self.grupos.items():
            out[cl] = dict(clave=cl, materia=g.ofreceMateria.claveMateria, nombre=g.ofreceMateria.nombreMateria, creditos=g.ofreceMateria.creditos,
                           tipo=type(g.ofreceMateria).__name__, modalidad=g.tieneModalidad.nombreModalidad, cupo=g.cupo,
                           bloques=[(h.diaSemana, h.inicioMinutos, h.finMinutos, h.turno) for h in g.tieneHorario])
        return out

    def limites_creditos(self):
        return self.restriccion.cargaMinimaCreditos, self.restriccion.cargaMaximaCreditos

    def verificar_consistencia(self):
        """Opcional: razonador HermiT (requiere Java)."""
        with self.o: sync_reasoner_hermit(infer_property_values=False)
        return True

    # ------------------------------------------------------------ registro de la recomendación en la ontología
    def registrar_recomendacion(self, matricula, res, ctx, phi, traza, v):
        """Guarda Recomendacion, Agentes y TrazaEjecucion como individuos de la ontología (trazabilidad/auditoría)."""
        from datetime import datetime
        o = self.o; e = self.estudiantes[matricula]
        nombres = {"Historial": "AgenteHistorial", "Carga": "AgenteCarga", "Horarios": "AgenteHorarios"}
        with o:
            ag = {}
            for k, cls in nombres.items():
                a = getattr(o, cls)("ag_" + k); a.nombreAgente = k; a.valorShapley = float(phi.get(k, 0)); ag[k] = a
            mgr = o.AgenteManager("ag_Manager"); mgr.nombreAgente = "Manager"; ag["Manager"] = mgr
            m = res["mejor"]; r = o.Recomendacion(f"rec_{matricula}"); r.recomiendaA = e; r.recomendacionParaPeriodo = self.periodo
            r.generadaPor = mgr; r.sujetaARestriccion = self.restriccion
            for g in m["grupos"]:
                r.incluyeGrupo.append(self.grupos[g]); r.sugiereMateria.append(self.grupos[g].ofreceMateria)
            r.puntajeRecomendacion = float(m["Score"]); r.avanceAcademico = float(m["Av"]); r.compatibilidadHorario = float(m["Ho"])
            r.cargaEquilibrada = float(m["Ca"]); r.cumplimientoPreferencias = float(m["Pr"]); r.fechaGeneracion = datetime.now()
            for i, ev in enumerate(traza.eventos):
                t = o.TrazaEjecucion(f"traza_{matricula}_{i}"); t.marcaTiempo = datetime.fromisoformat(ev["timestamp"]); t.tareaEjecutada = ev["task"]
                t.tiempoEjecucion = float(ev["execution_time"]); t.exito = bool(ev["success"])
                if ev["score"] is not None: t.scoreTraza = float(ev["score"])
                key = {"AgenteHistorial": "Historial", "AgenteCarga": "Carga", "AgenteHorarios": "Horarios"}.get(ev["agent"], "Manager")
                t.trazaDeAgente = ag[key]; t.trazaDeRecomendacion = r

    def guardar(self, ruta):
        """Guarda la ontología poblada (abrir en Protégé para ver individuos)."""
        self.o.save(file=str(ruta), format="rdfxml")
