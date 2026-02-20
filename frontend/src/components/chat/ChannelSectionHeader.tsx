import type { ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';

interface ChannelSectionHeaderProps {
  title: string;
  count: number;
  defaultOpen?: boolean;
  rightAction?: ReactNode;
  children: ReactNode;
}

export function ChannelSectionHeader({
  title,
  count,
  defaultOpen = true,
  rightAction,
  children,
}: ChannelSectionHeaderProps) {
  return (
    <Collapsible defaultOpen={defaultOpen}>
      <div className="flex items-center justify-between px-2 py-1">
        <CollapsibleTrigger className="flex items-center gap-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground">
          <ChevronDown className="size-3 transition-transform data-[state=closed]:-rotate-90" />
          {title} ({count})
        </CollapsibleTrigger>
        {rightAction}
      </div>
      <CollapsibleContent>{children}</CollapsibleContent>
    </Collapsible>
  );
}
