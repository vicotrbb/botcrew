import { useState } from 'react';
import { Outlet } from 'react-router';
import { Sidebar } from './Sidebar';

export function MainLayout() {
  const [isChatOpen, setIsChatOpen] = useState(true);

  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar
        isChatOpen={isChatOpen}
        onToggleChat={() => setIsChatOpen((prev) => !prev)}
      />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
      {isChatOpen && (
        <aside className="w-[380px] border-l border-border flex-shrink-0">
          <div className="p-4 text-sm text-muted-foreground">Chat panel</div>
        </aside>
      )}
    </div>
  );
}
