import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RagConfigSwitch } from "@/components/rag/RagConfigSwitch";
import { McpDataTable } from "@/components/mcp/McpDataTable";
import { AuditLog } from "@/components/mcp/AuditLog";
import { Database, Lock } from "lucide-react";

export function RightPanel() {
  return (
    <aside className="flex h-full w-[22rem] flex-col border-l border-border bg-sidebar/60 backdrop-blur">
      <Tabs defaultValue="rag" className="flex h-full min-h-0 flex-col">
        <div className="border-b border-border p-3">
          <TabsList className="grid w-full grid-cols-1">
            <TabsTrigger value="rag" className="gap-1.5">
              <Database className="size-3.5" /> RAG
            </TabsTrigger>
           
          </TabsList>
        </div>

        <TabsContent value="rag" className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-4">
          <div className="mb-3">
            <h3 className="font-display text-sm font-semibold">Configuración del RAG</h3>
            <p className="text-[11px] text-muted-foreground">
              Compara dos estrategias de chunking del corpus.
            </p>
          </div>
          <RagConfigSwitch />
        </TabsContent>

        
      </Tabs>
    </aside>
  );
}
