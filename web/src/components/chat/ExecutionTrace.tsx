import type { ExecutionTrace } from "@/lib/types";
import { AGENT_META } from "@/lib/agent-meta";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Activity, Clock, Cpu, Wrench } from "lucide-react";

export function ExecutionTraceView({ trace }: { trace: ExecutionTrace }) {
  const meta = AGENT_META[trace.agent];
  const Icon = meta.icon;

  return (
    <Accordion type="single" collapsible className="mt-3 w-full">
      <AccordionItem value="trace" className="overflow-hidden rounded-lg border border-border bg-card/40">
        <AccordionTrigger className="px-3 py-2 text-xs hover:no-underline">
          <span className="flex items-center gap-2">
            <Activity className="size-3.5 text-muted-foreground" />
            <span className="font-medium">Trazas de Ejecución e Inteligencia</span>
            <span className="text-muted-foreground">(Langfuse)</span>
          </span>
        </AccordionTrigger>
        <AccordionContent className="space-y-3 px-3 pb-3 text-xs">
          <div className={`flex items-center gap-2 rounded-md ${meta.bg} px-2.5 py-1.5 ring-1 ${meta.ring}`}>
            <Icon className={`size-3.5 ${meta.color}`} />
            <span className={`font-medium ${meta.color}`}>{meta.label}</span>
            {trace.ragConfig && (
              <span className="ml-auto rounded bg-background/40 px-1.5 py-0.5 text-[10px] text-muted-foreground">
                Config: {trace.ragConfig === "fija" ? "Fragmentación Fija" : "Fragmentación Semántica"}
              </span>
            )}
          </div>

          <div className="grid grid-cols-3 gap-2">
            <Stat icon={Clock} label="Latencia" value={`${(trace.latencyMs / 1000).toFixed(2)}s`} />
            <Stat icon={Cpu} label="Tokens in" value={trace.tokens.input.toString()} />
            <Stat icon={Cpu} label="Tokens out" value={trace.tokens.output.toString()} />
          </div>

          <div>
            <div className="mb-1.5 flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
              <Wrench className="size-3" /> Herramientas invocadas
            </div>
            <ul className="space-y-1">
              {trace.tools.map((t, i) => (
                <li key={i} className="rounded-md border border-border bg-background/40 px-2 py-1.5 font-mono text-[11px]">
                  <span className="text-primary">{t.name}</span>
                  <span className="text-muted-foreground">({JSON.stringify(t.args)})</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="text-[10px] text-muted-foreground">
            rol auditado: <span className="text-foreground">{trace.role}</span>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

function Stat({ icon: Icon, label, value }: { icon: typeof Clock; label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-background/40 px-2 py-1.5">
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-muted-foreground">
        <Icon className="size-3" /> {label}
      </div>
      <div className="mt-0.5 font-mono text-xs text-foreground">{value}</div>
    </div>
  );
}
