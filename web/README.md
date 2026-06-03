# Plan: Sistema Multi-Agente Avanzado (RAG + MCP + Memoria)

SPA frontend-first con mocks, lista para conectar backend real más adelante. Stack actual del proyecto (TanStack Start + Tailwind v4 + shadcn/ui + Lucide) — no se introduce `react-router-dom` ni se rompe la arquitectura existente. El proyecto ya despliega correctamente; "preparación para Vercel" se traduce a build limpio + `.env.example`.

## Diseño visual

- Tema oscuro elegante slate/indigo como default, toggle claro/oscuro.
- Tipografía: Space Grotesk (headings) + Inter (body).
- Tokens semánticos en `src/styles.css` (oklch): `--background`, `--panel`, `--primary` (indigo), `--accent`, `--agent-rag`, `--agent-web`, `--agent-mcp`, `--agent-summary` para colorear trazas por agente.
- Layout principal de 3 columnas (sidebar izq · chat · panel der), responsive: en mobile los paneles laterales se vuelven Sheets.

## Estructura de archivos

```text
src/
  routes/
    index.tsx                      # monta <AppShell/>
  components/
    layout/
      AppShell.tsx                 # grid 3 columnas + theme toggle
      LeftSidebar.tsx              # sesiones + perfil
      RightPanel.tsx               # tabs RAG | MCP
    chat/
      ChatPanel.tsx                # lista mensajes + input + auto-scroll
      MessageBubble.tsx            # user vs orquestador
      OrchestratorThinking.tsx     # animación "delegando tarea…"
      ExecutionTrace.tsx           # accordion Langfuse (agente, latencia, tokens, tools)
      SourceCitations.tsx          # tarjetas autor/archivo/fecha/fragmento
    rag/
      RagConfigSwitch.tsx          # tabs Fija vs Semántica
      RagComparisonHint.tsx        # nota visual del impacto
    mcp/
      McpDataTable.tsx             # cuenta, saldo, transacciones
      MaskToggle.tsx               # enmascarar datos sensibles
      AuditLog.tsx                 # log de llamadas a tools MCP
    sessions/
      SessionList.tsx
      NewSessionButton.tsx
      UserProfileCard.tsx          # Estudiante/Profesor/Auditor
  context/
    SessionsContext.tsx            # sesiones + mensaje activo
    RagConfigContext.tsx           # config 1 vs 2
    McpContext.tsx                 # datos simulados + máscara + audit log
    UserRoleContext.tsx
  hooks/
    useMockOrchestrator.ts         # enruta pregunta → agente → respuesta mock
    useAutoScroll.ts
  mocks/
    fixtures.ts                    # respuestas RAG/Web/MCP predefinidas
    sources.ts                     # citas con autor/archivo/fecha
    transactions.ts                # datos bancarios simulados
  lib/
    types.ts                       # Message, Trace, Citation, Agent, etc.
.env.example                       # VITE_API_BACKEND_URL=
```

## Lógica de mocks (`useMockOrchestrator`)

Detecta intent por keywords y devuelve un payload tipado `{ answer, agent, trace, citations? }` tras un delay simulado (800–1500ms):

1. Keywords académicas (gradiente, apuntes, paper, definición) → agente **RAG**, devuelve citas de `mocks/sources.ts` (incluye "apuntes de Carlos").
2. Keywords temporales/externas (últimas, noticias, hoy, esta semana, OpenAI) → agente **Web Search**.
3. Keywords transaccionales (cuenta, transacción, saldo, sospechoso, número de cuenta) → agente **MCP**, llama tool `get_transaction_by_id`, agrega entrada al `AuditLog`, respeta el toggle de máscara.
4. Fallback → agente **Resumidor**.

Cada respuesta produce una `Trace` con: agente, latencia mock, tokens mock, tools invocadas, y (si aplica) configuración RAG activa.

## Sesiones y memoria

- `SessionsContext` mantiene array de sesiones en `localStorage` (memoria histórica simulada). Cada sesión guarda mensajes + trazas.
- "Nueva Sesión" crea sesión vacía y la activa.
- Perfil de usuario (Estudiante/Profesor/Auditor) cambia un badge visible y se incluye en el payload de trazas para mostrar el rol auditado.

## Panel derecho

- **Tab RAG**: switch entre "Fragmentación Fija (512 tokens, overlap 50)" y "Fragmentación Semántica (chunks por embedding)". El switch afecta el contenido de citas devueltas por el mock (mismas fuentes, distinto fragmento/score) para que la comparación sea visible.
- **Tab MCP**: tabla con cuenta enmascarable (`****1234`), saldo, lista de transacciones (incluye una "transacción de madrugada" marcada). Toggle de máscara afecta cuenta, saldo y montos. AuditLog debajo lista cada llamada (`tool`, `timestamp`, `rol`, `argumentos`).

## Detalles técnicos

- Sin `react-router-dom`: TanStack Router ya está en uso; toda la app vive en `routes/index.tsx`.
- Todo el estado en Context + `useState`/`useReducer`, sin backend.
- `.env.example` con `VITE_API_BACKEND_URL=` y comentario indicando dónde se consumirá (placeholder en `useMockOrchestrator`).
- Tipado estricto, sin dependencias nuevas más allá de las ya presentes (shadcn, lucide, framer-motion ya disponible vía tw-animate-css; se añade `motion` solo si hace falta para la animación del orquestador — preferentemente con CSS/Tailwind para evitar dependencias).
- Build de Vercel: el template TanStack Start ya compila a edge; no se modifica `vite.config.ts`.

## Fuera de alcance (explícito)

- No se conecta backend real, Langfuse real, ni MCP real — todo simulado.
- No se añade auth ni Lovable Cloud (no fue pedido y rompería el alcance frontend-first).
- No se implementa i18n; UI en español directo.
