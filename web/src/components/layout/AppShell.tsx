import { LeftSidebar } from "./LeftSidebar";
import { RightPanel } from "./RightPanel";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { SessionsProvider } from "@/context/SessionsContext";
import { RagConfigProvider } from "@/context/RagConfigContext";
import { UserRoleProvider } from "@/context/UserRoleContext";
import { McpProvider } from "@/context/McpContext";
import { SearchModeProvider } from "@/context/SearchModeContext";

export function AppShell() {
  return (
    <UserRoleProvider>
      <RagConfigProvider>
        <SearchModeProvider>
          <McpProvider>
            <SessionsProvider>
              <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
                <LeftSidebar />
                <ChatPanel />
                <RightPanel />
              </div>
            </SessionsProvider>
          </McpProvider>
        </SearchModeProvider>
      </RagConfigProvider>
    </UserRoleProvider>
  );
}
