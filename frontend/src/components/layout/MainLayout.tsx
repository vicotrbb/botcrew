import { Outlet } from 'react-router';
import { useChatStore } from '@/stores/chat-store';
import { Sidebar } from './Sidebar';
import { ChatPanel } from '@/components/chat/ChatPanel';

export function MainLayout() {
  const { isOpen: isChatOpen, toggle: toggleChat } = useChatStore();

  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar
        isChatOpen={isChatOpen}
        onToggleChat={toggleChat}
      />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
      {isChatOpen && (
        <aside className="w-[380px] border-l border-border flex-shrink-0 h-screen overflow-hidden">
          <ChatPanel />
        </aside>
      )}
    </div>
  );
}
