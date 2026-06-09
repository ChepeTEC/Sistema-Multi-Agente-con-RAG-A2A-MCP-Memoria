import { useState, type FormEvent } from "react";
import { useSessions } from "@/context/SessionsContext";
import { useOrchestrator } from "@/hooks/useOrchestrator";
import { useAutoScroll } from "@/hooks/useAutoScroll";
import { useSearchMode } from "@/context/SearchModeContext";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MessageBubble } from "./MessageBubble";
import { OrchestratorThinking } from "./OrchestratorThinking";
import { SearchModeToggle } from "./SearchModeToggle";
import { Send, Sparkles, Database, Globe, Lock } from "lucide-react";

const SUGGESTIONS = [
  { icon: Database, label: "¿Qué es el descenso del gradiente según los apuntes de Carlos?" },
  { icon: Globe,    label: "¿Cuáles son las últimas noticias de OpenAI de esta semana?" },
  { icon: Lock,     label: "Verificar transacciones sospechosas de la cuenta 1234" },
];

export function ChatPanel() {
  const { active } = useSessions();
  const { send, isThinking } = useOrchestrator();
  const { mode } = useSearchMode();
  const [input, setInput] = useState("");
  const scrollRef = useAutoScroll(active.messages.length + (isThinking ? 1 : 0));

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    const text = input;
    setInput("");
    void send(text);
  };

  const isEmpty = active.messages.length === 0;

  return (
    <section className="flex h-full min-w-0 flex-1 flex-col bg-background bg-grid">
      {/* Header */}
      <header className="flex items-center justify-between gap-3 border-b border-border bg-background/70 px-6 py-3 backdrop-blur">
        <div className="min-w-0">
          <h1 className="truncate font-display text-base font-semibold">{active.title}</h1>
          <p className="text-[11px] text-muted-foreground">
            Orquestación multi-agente · RAG + Web Search + MCP
          </p>
        </div>
        <SearchModeToggle />
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="scrollbar-thin min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-6 px-6 py-6">
          {isEmpty ? (
            <EmptyState onPick={(q) => void send(q)} />
          ) : (
            active.messages.map((m) => <MessageBubble key={m.id} msg={m} />)
          )}
          {isThinking && <OrchestratorThinking />}
        </div>
      </div>

      {/* Composer */}
      <form
        onSubmit={submit}
        className="border-t border-border bg-background/80 px-6 py-4 backdrop-blur"
      >
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-border bg-card/60 p-2 focus-within:border-primary/60 focus-within:glow-ring">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Pregunta al Orquestador… (Enter para enviar · Shift+Enter para salto de línea)"
            className="min-h-[44px] max-h-40 resize-none border-0 bg-transparent focus-visible:ring-0"
            disabled={isThinking}
          />
          <Button
            type="submit"
            size="icon"
            disabled={isThinking || !input.trim()}
            className="size-10 shrink-0 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Send className="size-4" />
          </Button>
        </div>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">
          {mode === "web"
            ? "Búsqueda en la web habilitada · el Orquestador puede delegar en Web Search, RAG o MCP."
            : "Búsqueda limitada al corpus de apuntes · las consultas informativas se resuelven con RAG."}
        </p>
      </form>
    </section>
  );

  function EmptyState({ onPick }: { onPick: (q: string) => void }) {
    return (
      <div className="flex flex-col items-center py-10 text-center">
        <div className="mb-4 grid size-14 place-items-center rounded-2xl bg-primary/15 ring-1 ring-primary/40 glow-ring">
          <Sparkles className="size-6 text-primary" />
        </div>
        <h2 className="font-display text-2xl font-semibold tracking-tight">
          Sistema Multi-Agente con RAG, MCP y Memoria
        </h2>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          Prueba los tres flujos del sistema. El Orquestador delegará la consulta al agente
          especializado y mostrará las trazas, fuentes y auditoría.
        </p>
        <div className="mt-6 grid w-full max-w-2xl gap-2 sm:grid-cols-3">
          {SUGGESTIONS.map((s, i) => {
            const Icon = s.icon;
            return (
              <button
                key={i}
                onClick={() => onPick(s.label)}
                className="group rounded-xl border border-border bg-card/40 p-3 text-left text-sm transition hover:border-primary/40 hover:bg-card"
              >
                <Icon className="mb-2 size-4 text-primary" />
                <span className="block leading-snug text-foreground/90 group-hover:text-foreground">
                  {s.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    );
  }
}
