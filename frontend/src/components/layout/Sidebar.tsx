import { NavLink } from 'react-router';
import { Bot, BookOpen, ClipboardList, FolderKanban, KeyRound, MessageSquare, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

interface SidebarProps {
  isChatOpen: boolean;
  onToggleChat: () => void;
}

export function Sidebar({ isChatOpen, onToggleChat }: SidebarProps) {
  return (
    <div className="w-56 border-r border-border bg-background flex flex-col h-full flex-shrink-0">
      <div className="p-4">
        <span className="text-sm font-mono font-semibold tracking-tight">
          botcrew
        </span>
      </div>

      <nav className="flex-1 px-2 space-y-1">
        <NavLink
          to="/agents"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
            )
          }
        >
          <Bot className="size-4" />
          Agents
        </NavLink>
        <NavLink
          to="/projects"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
            )
          }
        >
          <FolderKanban className="size-4" />
          Projects
        </NavLink>
        <NavLink
          to="/tasks"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
            )
          }
        >
          <ClipboardList className="size-4" />
          Tasks
        </NavLink>
        <NavLink
          to="/skills"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
            )
          }
        >
          <BookOpen className="size-4" />
          Skills
        </NavLink>
        <NavLink
          to="/secrets"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
            )
          }
        >
          <KeyRound className="size-4" />
          Secrets
        </NavLink>
        <NavLink
          to="/integrations"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
            )
          }
        >
          <Settings className="size-4" />
          Integrations
        </NavLink>
      </nav>

      <div className="px-2 pb-2">
        <Separator className="mb-2" />
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleChat}
          className={cn(
            'w-full justify-start gap-2',
            isChatOpen
              ? 'text-foreground'
              : 'text-muted-foreground',
          )}
        >
          <MessageSquare className="size-4" />
          Chat
        </Button>
      </div>
    </div>
  );
}
