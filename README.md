# Sistema-Multi-Agente-con-RAG-A2A-MCP-Memoria
Sistema multi-agente con RAG para consultar apuntes del curso de Inteligencia Artificial. Incluye orquestador, agentes especializados, base vectorial, respuestas fundamentadas, observabilidad con Langfuse y arquitectura extensible hacia memoria, búsqueda web y MCP.

## Agente Web Search

El agente `WebSearchAgent` consulta internet mediante Tavily y redacta la
respuesta final mediante un modelo de Gemini configurable. Tavily se utiliza
únicamente como herramienta de búsqueda. Cada búsqueda requiere una
justificación para que posteriormente el orquestador pueda registrar por qué
utilizó una fuente externa.

Los agentes dependen del protocolo común `LLMClient`. La implementación
`GeminiClient` se utiliza por defecto en Web Search y permite agregar otros
proveedores posteriormente sin cambiar la lógica del agente.

1. Cree una API key en Tavily.
2. Cree una API key en Gemini.
3. Copie `.env.example` como `.env` y configure `TAVILY_API_KEY` y
   `GEMINI_API_KEY`.
4. Seleccione el modelo mediante `WEB_SEARCH_LLM_MODEL`.
5. Instale las dependencias con `pip install -r requirements.txt`.

Ejemplo:

```python
from src.agents.web_search_agent import WebSearchAgent

agent = WebSearchAgent()
result = agent.answer(
    question="¿Cuáles son las novedades recientes sobre agentes de IA?",
    justification="El usuario solicitó información reciente de internet."
)

print(result["answer"])
print(result["sources"])
```
