import { Plus } from 'lucide-react';
import type { Channel } from '@/types/channel';
import type { AgentSummary } from '@/types/agent';
import { Button } from '@/components/ui/button';
import { ChannelSectionHeader } from './ChannelSectionHeader';
import { ChannelItem } from './ChannelItem';

interface ChannelSelectorProps {
  channels: Channel[];
  activeChannelId: string | null;
  onChannelSelect: (id: string) => void;
  onCreateChannel: () => void;
  unreadCounts: Record<string, number>;
  agents: AgentSummary[];
  dmChannelMap: Record<string, string>;
  onAgentDmSelect: (agentId: string) => void;
}

/** Split channels into sidebar sections by channel_type. */
function categorizeChannels(channels: Channel[]) {
  const sections = {
    project: [] as Channel[],
    task: [] as Channel[],
    custom: [] as Channel[],
    dm: [] as Channel[],
  };

  for (const ch of channels) {
    switch (ch.channel_type) {
      case 'project':
        sections.project.push(ch);
        break;
      case 'task':
        sections.task.push(ch);
        break;
      case 'custom':
        sections.custom.push(ch);
        break;
      case 'dm':
        sections.dm.push(ch);
        break;
      default:
        // 'shared' falls into custom as a fallback
        sections.custom.push(ch);
    }
  }

  // Sort each section by most recent activity (updated_at desc)
  for (const key of Object.keys(sections) as (keyof typeof sections)[]) {
    sections[key].sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
  }

  return sections;
}

export function ChannelSelector({
  channels,
  activeChannelId,
  onChannelSelect,
  onCreateChannel,
  unreadCounts,
  agents,
  dmChannelMap,
  onAgentDmSelect,
}: ChannelSelectorProps) {
  const sections = categorizeChannels(channels);

  return (
    <div className="flex flex-col overflow-y-auto border-b border-border max-h-[40vh]">
      {/* Projects */}
      <ChannelSectionHeader
        title="Projects"
        count={sections.project.length}
        defaultOpen
      >
        {sections.project.map((ch) => (
          <ChannelItem
            key={ch.id}
            channel={ch}
            isActive={ch.id === activeChannelId}
            unreadCount={unreadCounts[ch.id] ?? 0}
            onClick={() => onChannelSelect(ch.id)}
          />
        ))}
      </ChannelSectionHeader>

      {/* Tasks */}
      <ChannelSectionHeader
        title="Tasks"
        count={sections.task.length}
        defaultOpen
      >
        {sections.task.map((ch) => (
          <ChannelItem
            key={ch.id}
            channel={ch}
            isActive={ch.id === activeChannelId}
            unreadCount={unreadCounts[ch.id] ?? 0}
            onClick={() => onChannelSelect(ch.id)}
          />
        ))}
      </ChannelSectionHeader>

      {/* Custom */}
      <ChannelSectionHeader
        title="Custom"
        count={sections.custom.length}
        defaultOpen
        rightAction={
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={onCreateChannel}
            aria-label="Create channel"
          >
            <Plus className="size-3.5" />
          </Button>
        }
      >
        {sections.custom.map((ch) => (
          <ChannelItem
            key={ch.id}
            channel={ch}
            isActive={ch.id === activeChannelId}
            unreadCount={unreadCounts[ch.id] ?? 0}
            onClick={() => onChannelSelect(ch.id)}
          />
        ))}
      </ChannelSectionHeader>

      {/* DMs */}
      <ChannelSectionHeader
        title="DMs"
        count={agents.length}
        defaultOpen
      >
        {agents.map((agent) => {
          const dmChannelId = dmChannelMap[agent.id];
          const isActive = dmChannelId === activeChannelId;

          // Synthetic channel-like object for display
          const syntheticChannel: Channel = {
            id: dmChannelId ?? `dm-pending-${agent.id}`,
            name: agent.name,
            description: agent.id,
            channel_type: 'dm',
            creator_user_identifier: null,
            created_at: '',
            updated_at: '',
          };

          return (
            <ChannelItem
              key={`dm-${agent.id}`}
              channel={syntheticChannel}
              isActive={isActive}
              unreadCount={dmChannelId ? (unreadCounts[dmChannelId] ?? 0) : 0}
              onClick={() => onAgentDmSelect(agent.id)}
              agentName={agent.name}
            />
          );
        })}
      </ChannelSectionHeader>
    </div>
  );
}
