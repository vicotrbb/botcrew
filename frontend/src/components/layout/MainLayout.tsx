import { useRef, useCallback } from 'react';
import { Outlet } from 'react-router';
import { useChatStore } from '@/stores/chat-store';
import { Sidebar } from './Sidebar';
import { ChatPanel } from '@/components/chat/ChatPanel';

export function MainLayout() {
  const { isOpen: isChatOpen, toggle: toggleChat, panelWidth, setPanelWidth } =
    useChatStore();

  const isResizing = useRef(false);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      isResizing.current = true;
      e.preventDefault();

      const handleMouseMove = (e: MouseEvent) => {
        if (!isResizing.current) return;
        const newWidth = window.innerWidth - e.clientX;
        setPanelWidth(newWidth); // clamping happens in the store
      };

      const handleMouseUp = () => {
        isResizing.current = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [setPanelWidth],
  );

  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar isChatOpen={isChatOpen} onToggleChat={toggleChat} />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
      {isChatOpen && (
        <aside
          style={{ width: panelWidth }}
          className="relative border-l border-border flex-shrink-0 h-screen overflow-hidden"
        >
          <div
            onMouseDown={handleMouseDown}
            className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/40 z-10"
          />
          <ChatPanel />
        </aside>
      )}
    </div>
  );
}
