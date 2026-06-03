import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Sistema Multi-Agente · RAG, MCP y Memoria" },
      {
        name: "description",
        content:
          "Interfaz interactiva del Sistema Multi-Agente con orquestación RAG, MCP transaccional y memoria histórica de sesiones.",
      },
      { property: "og:title", content: "Sistema Multi-Agente · RAG, MCP y Memoria" },
      {
        property: "og:description",
        content:
          "Demo frontend del Sistema Multi-Agente Avanzado con trazas Langfuse, citas, auditoría MCP y comparación de configuraciones RAG.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  return <AppShell />;
}
