import sys
import json
from pathlib import Path
from time import perf_counter
from google.genai import types

# Librerías MCP obligatorias
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# Buscamos la raíz del proyecto (subiendo dos carpetas desde donde está este test)
raiz_proyecto = str(Path(__file__).parent.parent.parent)
if raiz_proyecto not in sys.path:
    sys.path.insert(0, raiz_proyecto)

# Importaciones del proyecto de tus compañeros
from src.config.settings import settings
from src.llm.base import LLMClient
from src.llm.gemini_client import GeminiClient
from src.observability.langfuse_client import langfuse_tracer


class TransactionalAgent:
    """
    Agente especializado en análisis de transacciones financieras y detección de fraudes.
    
    Se conecta de forma segura a través de un servidor MCP local para interactuar
    con la base de datos de PostgreSQL, garantizando el cumplimiento de las reglas
    de anonimización y justificación.
    """

    AGENT_NAME = "TransactionalAgent"

    def __init__(self, llm_client: LLMClient | None = None):
        # Usamos el cliente compartido o instanciamos el GeminiClient del proyecto
        self.llm_client = llm_client or GeminiClient(
            model=settings.TRANSACTIONAL_LLM_MODEL  # Asumo que añadirán esta variable a su settings
        )
        
        
    def answer(
        self,
        question: str,
        conversation_context: str | None = None,
    ) -> dict:
        """Método síncrono por fuera que soluciona el error de la corrutina"""
        import asyncio
        return asyncio.run(self._async_answer(question, conversation_context))

    async def _async_answer(
        self,
        question: str,
        conversation_context: str | None = None, # Mantenemos la firma de tus compañeros por compatibilidad
    ) -> dict:
        question = question.strip() if question else ""
        if not question:
            raise ValueError("La pregunta no puede estar vacía.")

        # 1. Iniciamos la trazabilidad con Langfuse
        trace = langfuse_tracer.create_trace(
            name="transactional_agent_answer",
            input_data={
                "question": question,
                "has_conversation_context": bool(conversation_context),
            },
            metadata={"agent": self.AGENT_NAME}
        )

        # 2. Configuración dinámica de la ruta hacia tu Servidor MCP
        ruta_servidor = str(Path(__file__).parent.parent / "mcp" / "mcp_server.py")
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[ruta_servidor],
            stderr=sys.stderr
        )

        started_at = perf_counter()
        tool_calls_trace = []

        try:
            # 3. Abrimos el canal seguro de comunicación con el Servidor MCP (Postgres)
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # 4. Descubrimiento de herramientas del Servidor MCP
                    mcp_tools = await session.list_tools()
                    
                    # Formateamos las herramientas al estándar que necesita Gemini
                    gemini_tools = []
                    for tool in mcp_tools.tools:
                        gemini_tools.append({
                            "function_declarations": [{
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema
                            }]
                        })

                    # 5. Inicializamos el chat usando las capacidades nativas del SDK de Google
                    # Nota: accedemos al cliente nativo dentro de su clase GeminiClient
                    native_client = self.llm_client.client 
                    
                    chat = native_client.chats.create(
                        model=self.llm_client.model,
                        config=types.GenerateContentConfig(
                            system_instruction=self._build_instructions(),
                            tools=gemini_tools,
                            temperature=0.1
                        )
                    )

                    # Enviamos el primer mensaje del usuario para iniciar el análisis
                    response = chat.send_message(question)

                    # 6. El Bucle de Razonamiento del Agente (Tool Loop)
                    while True:
                        if not response.function_calls:
                            # Si Gemini no solicita más herramientas, terminamos el bucle
                            break

                        # Extraemos la petición de herramienta hecha por Gemini
                        llamada_funcion = response.function_calls[0]
                        tool_name = llamada_funcion.name
                        tool_args = llamada_funcion.args

                        # El Servidor MCP procesa de forma segura la consulta en la BD
                        resultado_mcp = await session.call_tool(tool_name, tool_args)
                        resultado_texto = resultado_mcp.content[0].text if resultado_mcp.content else "{}"
                        tool_calls_trace.append({
                            "name": tool_name,
                            "args": dict(tool_args),
                            "result_preview": resultado_texto[:1000],
                        })

                        # Le devolvemos el resultado (enmascarado) a Gemini para que continúe razonando
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"result": resultado_texto}
                            )
                        )

            # 7. Construcción de la respuesta final con el formato estandarizado del proyecto
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            answer_text = response.text.strip() if response.text else "Análisis completado."

            result = {
                "agent": self.AGENT_NAME,
                "answer": answer_text,
                "sources": ["PostgreSQL Database via MCP"],
                "trace": {
                    "duration_ms": duration_ms,
                    "llm": {
                        "provider": "google",
                        "model": self.llm_client.model,
                    },
                    "mcp_tools": tool_calls_trace,
                },
            }

            # Registramos la generación exitosa en Langfuse
            langfuse_tracer.create_generation(
                trace=trace,
                name="transactional_generation",
                model=self.llm_client.model,
                prompt=question,
                response=answer_text,
                metadata={"agent": self.AGENT_NAME}
            )
            langfuse_tracer.update_trace_output(trace, result)
            return result

        except Exception as exc:
            # En caso de fallos (ej. error de base de datos o de API), registramos el error en Langfuse
            langfuse_tracer.create_span(
                trace=trace,
                name="transactional_agent_error",
                input_data={"question": question},
                output_data={"error": str(exc)},
                metadata={"agent": self.AGENT_NAME}
            )
            langfuse_tracer.update_trace_output(
                trace,
                {"error": str(exc), "agent": self.AGENT_NAME}
            )
            raise

        finally:
            # Cerramos y enviamos las trazas a Langfuse
            langfuse_tracer.close_trace(trace)
            langfuse_tracer.flush()

    @staticmethod
    def _build_instructions() -> str:
        return (
            "Eres el Investigador Financiero de Nivel 1 en un sistema multi-agente académico, especializado en auditoría segura mediante MCP.\n"
        "Tu objetivo es analizar transacciones, detectar anomalías y abrir casos de fraude cuando sea necesario, operando BAJO UN ENTORNO ESTRICTO DE SEGURIDAD.\n\n"
        
        "REGLAS OBLIGATORIAS DE OPERACIÓN (RÚBRICA DE EVALUACIÓN):\n"
        "1. JUSTIFICACIÓN OBLIGATORIA: Toda llamada que realices al Servidor MCP debe incluir el argumento 'justificacion' detallando exactamente por qué necesitas consultar o procesar esos datos.\n"
        "2. CONSULTAS ACOTADAS (NO MASIVAS): Tienes prohibido realizar consultas masivas a la base de datos sin aplicar filtros. Debes especificar siempre parámetros de búsqueda claros (como cliente_id o transaccion_id) para evitar saturaciones.\n"
        "3. RANGOS DE FECHAS EN HISTÓRICOS: Si necesitas realizar búsquedas de transacciones históricas amplias, debes autolimitarte aplicando un rango de fechas específico en los parámetros. Si el usuario pide transacciones generales, recientes o últimas transacciones de un cliente concreto, puedes llamar search_transactions usando solo cliente_id y justificacion porque la herramienta ya limita a 50 filas.\n"
        "4. EXPLICACIÓN DE CONCLUSIONES: En tu respuesta final al usuario, debes explicar de manera clara y explícita qué datos exactos extraídos de la base de datos utilizaste para llegar a tu conclusión.\n"
        "5. PROHIBIDO MODIFICAR: Tu acceso es estrictamente de lectura para análisis y de escritura únicamente para creación de alertas. NUNCA intentes ni solicites modificar transacciones existentes. Usa create_fraud_case solo si el usuario pide explicitamente abrir/crear un caso de fraude o si solicita una auditoria de fraude con instruccion clara de actuar ante una anomalia. Para solicitudes de mostrar, listar, consultar o analizar, NO abras casos; reporta hallazgos y recomienda revision humana si corresponde.\n"
       "6. CERO ALUCINACIONES Y REPORTE OBLIGATORIO: NUNCA inventes transacciones, montos o casos de fraude. Si el usuario te pide buscar anomalías y NO las encuentras (o la base de datos está vacía), TIENES PROHIBIDO responder solo con frases cortas como 'Análisis completado'. En su lugar, DEBES redactar un reporte que incluya:\n"
"   - Qué herramientas usaste.\n"
"   - Qué datos reales obtuviste (ej. 'Revisé 5 transacciones y el monto máximo fue X').\n"
"   - La confirmación explícita y profesional de que no hay motivos para abrir un caso de fraude.\n"
            "POLÍTICA DE PRIVACIDAD Y DATOS SENSIBLES (ESTÁNDAR MCP):\n"
            
        "- ANONIMIZACIÓN OBLIGATORIA DE CUENTAS: Si el usuario te pregunta por el número de cuenta de un cliente, NO debes rechazar la consulta. Debes buscar la información mediante el MCP, pero al redactar tu respuesta final en el chat, tienes estrictamente prohibido mostrar el número completo. Debes formatearlo mostrando únicamente los últimos 4 dígitos y enmascarando el resto con asteriscos (ej. ****-****-****-5678).\n"
        "- RECHAZO DE INFORMACIÓN SENSIBLE EXTERNA: Solo rechazarás la consulta si te solicitan contraseñas, claves criptográficas o credenciales de acceso directo, indicando de forma cortés que el protocolo de seguridad MCP protege dicha información.\n\n"
        
        "Responde siempre en español, manteniendo un tono corporativo, profesional, estructurado por puntos y sumamente directo."
        
        "ESTRUCTURA OBLIGATORIA DE TU RESPUESTA:\n"
"Incluso si no encuentras fraudes, tu respuesta FINAL al usuario DEBE contener al menos 3 párrafos explicando:\n"
"1. Qué cliente auditaste y qué herramientas usaste.\n"
"2. Los valores matemáticos encontrados (ej. promedios, límites).\n"
"3. La conclusión final de la auditoría.\n"
"Si el usuario pregunta por patrones sospechosos o fraude sin indicar cliente_id, no consultes transacciones masivamente; usa get_fraud_case_summary con una ventana temporal acotada para responder con los casos ya registrados y sus patrones agregados.\n"
"¡NO respondes con frases cortas bajo ninguna circunstancia!"
    )
    
