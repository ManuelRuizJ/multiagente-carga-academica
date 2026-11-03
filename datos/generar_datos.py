# -*- coding: utf-8 -*-
"""Genera datos/catalogo_ejemplo.json (DATOS DE EJEMPLO: sustituir por el catálogo real de la Ibero)."""
import json, pathlib

def m(h, mi=0): return h * 60 + mi
MATERIAS = [  # clave, nombre, créditos, semestre, tipo, prerrequisitos, dificultad(1-5)
 ("MAT101", "Cálculo Diferencial", 8, 1, "obligatoria", [], 4),
 ("PRO101", "Programación I", 8, 1, "obligatoria", [], 3),
 ("MAT102", "Cálculo Integral", 8, 2, "obligatoria", ["MAT101"], 4),
 ("PRO102", "Programación II", 8, 2, "obligatoria", ["PRO101"], 3),
 ("MAT201", "Álgebra Lineal", 6, 3, "obligatoria", ["MAT101"], 3),
 ("PRO201", "Estructuras de Datos", 8, 3, "obligatoria", ["PRO102"], 4),
 ("BD201", "Bases de Datos", 8, 3, "obligatoria", ["PRO102"], 3),
 ("RED301", "Redes de Computadoras", 6, 4, "obligatoria", ["PRO102"], 3),
 ("SO301", "Sistemas Operativos", 8, 4, "obligatoria", ["PRO201"], 4),
 ("EST301", "Probabilidad y Estadística", 6, 4, "obligatoria", ["MAT102"], 3),
 ("IA401", "Inteligencia Artificial", 8, 5, "obligatoria", ["PRO201", "EST301"], 5),
 ("ING401", "Ingeniería de Software", 8, 5, "obligatoria", ["BD201"], 3),
 ("OPT501", "Computación en la Nube", 6, 6, "optativa", ["SO301"], 3),
 ("ELE501", "Ética Profesional", 4, 6, "electiva", [], 1),
]
DIAS = [("Lun", "Mié"), ("Mar", "Jue")]
MAN = [(m(7), m(9)), (m(9), m(11)), (m(11), m(13))]
TAR = [(m(14), m(16)), (m(16), m(18)), (m(18), m(20))]
grupos = []
for i, (cl, *_r) in enumerate(MATERIAS):
    a = dict(clave=f"{cl}-A", materia=cl, profesor=f"P{i % 5 + 1}", modalidad="presencial", cupo=30,
             horarios=[dict(dia=d, ini=MAN[i % 3][0], fin=MAN[i % 3][1]) for d in DIAS[i % 2]])
    b = dict(clave=f"{cl}-B", materia=cl, profesor=f"P{(i + 2) % 5 + 1}", modalidad=["enlinea", "hibrida", "presencial"][i % 3], cupo=30,
             horarios=[dict(dia=d, ini=TAR[(i + 1) % 3][0], fin=TAR[(i + 1) % 3][1]) for d in DIAS[(i + 1) % 2]])
    grupos.append(a)
    if cl in ("OPT501", "ELE501"): a["horarios"] = [dict(dia="Vie", ini=m(16), fin=m(19))]   # un solo grupo
    else: grupos.append(b)
ok = lambda c, cal=8.5: dict(materia=c, estado="aprobado", calificacion=cal, intento=1)
rp = lambda c: dict(materia=c, estado="reprobado", calificacion=5.0, intento=1)
base3 = ["MAT101", "PRO101", "MAT102", "PRO102", "MAT201", "PRO201", "BD201"]
est = [
 dict(matricula="E1", nombre="Alumno regular (ejemplo)", semestre=4, kardex=[ok(c) for c in base3],
      mensaje="Quiero una carga normal y, de preferencia, clases por la tarde."),
 dict(matricula="E2", nombre="Alumno con materias reprobadas (ejemplo)", semestre=4,
      kardex=[ok("MAT101"), ok("PRO101"), ok("PRO102"), ok("MAT201"), rp("MAT102"), rp("PRO201")],
      mensaje="Prefiero una carga ligera y que las clases sean presenciales."),
 dict(matricula="E3", nombre="Alumno avanzado (ejemplo)", semestre=6,
      kardex=[ok(c) for c in base3 + ["RED301", "SO301", "EST301"]],
      mensaje="Quiero clases en línea y por la tarde, con una carga ligera."),
]
datos = dict(
 programa=dict(nombre="Ingeniería en Sistemas (EJEMPLO)", creditosTotales=300),
 plan=dict(anio=2024, calificacionMinimaAprobatoria=7.0, cargaMinimaCreditos=18, cargaMaximaCreditos=36),
 periodo=dict(clave="2027-1", nombre="Ene-Jun 2027"),
 profesores=[dict(clave=f"P{k}", nombre=f"Profesor {k} (ejemplo)") for k in range(1, 6)],
 materias=[dict(clave=c, nombre=n, creditos=cr, semestre=s, tipo=t, prereq=p, dificultad=d) for c, n, cr, s, t, p, d in MATERIAS],
 grupos=grupos, estudiantes=est)
pathlib.Path(__file__).with_name("catalogo_ejemplo.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
print("materias", len(MATERIAS), "grupos", len(grupos), "estudiantes", len(est))
