# Agente de recomendación de carga académica (MAS + OWL + Shapley)

Prototipo del proyecto: **CrewAI (Process.hierarchical) + ontología OWL (owlready2) + Contract Net en Python + Valores de Shapley**.

## ¿Qué hace cada carpeta?
| Archivo | Qué es |
|---|---|
| `ontologia/P2_ontologia_carga_academica.owx` | Su ontología (clases y propiedades). Es la fuente de verdad. |
| `datos/catalogo_ejemplo.json` | **Datos de EJEMPLO** (materias, grupos, 3 alumnos). Hay que reemplazarlos por el catálogo real de la Ibero. |
| `mas/kb.py` | Carga el OWX, crea individuos con los datos y responde consultas (historial, prerrequisitos). |
| `mas/preferencias.py` | Interpreta el mensaje del alumno. Con Ollama (LLM) o por reglas; el LLM solo puede devolver valores del vocabulario de la ontología. |
| `mas/scoring.py` | Ecuación (1): Score = 0.30·Av + 0.25·Ho + 0.25·Ca + 0.20·Pr |
| `mas/coordinacion.py` | Los 3 agentes especialistas y el protocolo **Contract Net** (Python puro). |
| `mas/shapley.py` | Valores de Shapley exactos, ecuación (2). |
| `mas/trazas.py` | Trace Collector (guarda trazas en `resultados/`). |
| `mas/crew_mas.py` | Capa **CrewAI**: agentes, herramientas `@tool`, tasks y crew jerárquico con Ollama. |
| `main.py` | Punto de entrada. |

## Paso a paso (Windows/Mac/Linux)
1. Instalar Python 3.10–3.12 y Java (solo si quieren usar el razonador HermiT).
2. En una terminal, dentro de esta carpeta:
   ```
   python -m venv venv
   venv\Scripts\activate        (Mac/Linux: source venv/bin/activate)
   pip install -r requirements.txt
   ```
3. **Probar sin LLM** (ya funciona): `python main.py --escenarios`
   Imprime propuestas, Score, Shapley y guarda en `resultados/`: `tabla1.csv`, `resultados.json`, trazas y `ontologia_poblada.owl` (ábranla en Protégé: verán individuos y las recomendaciones).
4. **Probar con un mensaje propio**: `python main.py --matricula E1 --mensaje "quiero clases en línea por la tarde"`
5. **Con LLM local (Ollama)**:
   - Instalar Ollama (https://ollama.com) y ejecutar: `ollama pull llama3.1:8b`
   - Preferencias con LLM: `python main.py --escenarios --llm`
   - Orquestación completa con CrewAI: `python main.py --crewai --matricula E1`

## Cómo reemplazar los datos de ejemplo
Editen `datos/generar_datos.py` (o directamente `catalogo_ejemplo.json`) con materias, prerrequisitos, grupos y kárdex reales. Los horarios son en minutos desde las 00:00 (7:00 = 420).

## Qué está probado y qué no
- Probado: carga de la ontología, población, prerrequisitos, Contract Net, Shapley, trazas y registro en la ontología; construcción del crew y de las herramientas de CrewAI.
- **No probado**: la ejecución con Ollama (`--llm` y `--crewai`), porque requiere el modelo local. Los modelos pequeños pueden fallar al delegar en modo jerárquico; por eso la lógica crítica (prerrequisitos, choques, Score, Shapley) está en Python y el LLM solo orquesta e interpreta.
- Nota de diseño: CrewAI no permite herramientas en el manager jerárquico, así que `coordinar_carga` está asignada a los tres especialistas.

## Si el crew se atora (LLM lento o alucinando)
- Las herramientas **ignoran la matrícula que invente el LLM** (usan la del alumno en curso) y nunca lanzan excepciones: devuelven un JSON con el error y la ayuda.
- Cada agente tiene `max_iter` y `max_execution_time` para cortar bucles.
- Si el crew falla o lo interrumpen con **Ctrl+C**, `--crewai` ejecuta Contract Net directamente y muestra igual la recomendación ("respaldo determinista").
- En CPU cada llamada al LLM tarda ~1 min: para pruebas rápidas usen `python main.py --escenarios` (sin LLM) o `--llm` (solo interpretación de preferencias, 1 llamada).

## Error "ROCm error: invalid device function" (GPU AMD)
Es un fallo de **Ollama con la GPU**, no del código. Hay que obligar a Ollama a usar la CPU **antes** de correr el proyecto:
1. Detener el servicio: `sudo systemctl stop ollama` (Linux). 
2. Arrancarlo en CPU en otra terminal: `HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 OLLAMA_LLM_LIBRARY=cpu ollama serve`
   (para dejarlo fijo: `sudo systemctl edit ollama` y añadir esas variables en `[Service]` como `Environment="..."`).
3. Verificar que responde: `ollama run llama3.1:8b "hola"`. Si contesta, ya puede correr `python main.py --crewai --matricula E1`.
Para ir más rápido en CPU pueden probar un modelo más chico: `ollama pull llama3.2:3b` y `export OLLAMA_MODEL=llama3.2:3b` (es menos confiable usando herramientas).
`main.py --crewai` ahora hace una prueba de 1 token antes de lanzar el crew: si Ollama falla, avisa claro y usa el respaldo determinista.
# multiagente-carga-academica
