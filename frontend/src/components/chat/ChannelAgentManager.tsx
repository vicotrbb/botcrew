import { DragDropContext, Droppable, Draggable, type DropResult } from '@hello-pangea/dnd';
import { GripVertical, Info } from 'lucide-react';
import { toast } from 'sonner';
import { useAgents } from '@/hooks/use-agents';
import { useChannelMembers, useAddChannelMember, useRemoveChannelMember } from '@/hooks/use-channels';
import { StatusBadge } from '@/components/shared/StatusBadge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { ChannelType } from '@/types/channel';
import type { AgentStatus } from '@/types/agent';

interface ChannelAgentManagerProps {
  channelId: string;
  channelType: ChannelType;
}

export function ChannelAgentManager({ channelId, channelType }: ChannelAgentManagerProps) {
  // DM channels don't show agent management
  if (channelType === 'dm') return null;

  // Project and task channels show restricted view
  if (channelType === 'project' || channelType === 'task') {
    return <RestrictedView channelId={channelId} channelType={channelType} />;
  }

  // Custom and shared channels get full DnD management
  return <DndAgentManager channelId={channelId} />;
}

function RestrictedView({ channelId, channelType }: { channelId: string; channelType: 'project' | 'task' }) {
  const { data: allAgents } = useAgents();
  const { data: members, isLoading } = useChannelMembers(channelId);

  const agentLookup = new Map(
    (allAgents ?? []).map((a) => [a.id, { name: a.name, status: a.status }]),
  );

  const agentMembers = (members ?? []).filter((m) => m.agent_id != null);

  if (isLoading) {
    return (
      <div className="space-y-2 px-2">
        <div className="border rounded-lg p-3 min-h-[100px] bg-muted/30 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-2 px-2">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-medium">Channel Agents</h3>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="size-3.5 text-muted-foreground cursor-help" />
            </TooltipTrigger>
            <TooltipContent>
              Agents are managed at the {channelType} level
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <div className="border rounded-lg p-3 min-h-[60px] opacity-60 cursor-not-allowed">
        {agentMembers.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-2">
            No agents in this channel
          </p>
        ) : (
          agentMembers.map((m) => {
            const info = agentLookup.get(m.agent_id!);
            return (
              <div
                key={m.agent_id}
                className="flex items-center gap-2 p-2 mb-1 rounded bg-muted/50 text-sm"
              >
                <GripVertical className="size-3 text-muted-foreground/40 shrink-0" />
                <span className="truncate flex-1">{info?.name ?? m.agent_id}</span>
                {info && (
                  <StatusBadge status={info.status as AgentStatus} size="sm" showLabel={false} />
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function DndAgentManager({ channelId }: { channelId: string }) {
  const { data: allAgents, isLoading: agentsLoading } = useAgents();
  const { data: members, isLoading: membersLoading } = useChannelMembers(channelId);
  const addMember = useAddChannelMember();
  const removeMember = useRemoveChannelMember();

  const isLoading = agentsLoading || membersLoading;

  // Build set of assigned agent IDs from channel members
  const assignedAgentIds = new Set(
    (members ?? []).filter((m) => m.agent_id != null).map((m) => m.agent_id!),
  );

  // Available agents = all agents minus those already members
  const availableAgents = (allAgents ?? []).filter((a) => !assignedAgentIds.has(a.id));

  // Assigned agents from member list (agent members only)
  const assignedMembers = (members ?? []).filter((m) => m.agent_id != null);

  // Lookup for agent names/status
  const agentLookup = new Map(
    (allAgents ?? []).map((a) => [a.id, { name: a.name, status: a.status }]),
  );

  function handleDragEnd(result: DropResult) {
    if (!result.destination) return;
    const { source, destination, draggableId } = result;

    if (source.droppableId === 'available' && destination.droppableId === 'assigned') {
      addMember.mutate(
        { channelId, body: { agent_id: draggableId } },
        {
          onSuccess: () => {
            toast.success('Agent added to channel');
          },
          onError: () => {
            toast.error('Something went wrong. Please try again.');
          },
        },
      );
    } else if (source.droppableId === 'assigned' && destination.droppableId === 'available') {
      removeMember.mutate(
        { channelId, agentId: draggableId },
        {
          onSuccess: () => {
            toast.success('Agent removed from channel');
          },
          onError: () => {
            toast.error('Something went wrong. Please try again.');
          },
        },
      );
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-2 px-2">
        <h3 className="text-sm font-medium">Channel Agents</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="border rounded-lg p-3 min-h-[200px] bg-muted/30 animate-pulse" />
          <div className="border rounded-lg p-3 min-h-[200px] bg-muted/30 animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2 px-2">
      <h3 className="text-sm font-medium">Channel Agents</h3>
      <p className="text-xs text-muted-foreground mb-2">
        Drag agents between lists to add or remove them from this channel.
      </p>
      <DragDropContext onDragEnd={handleDragEnd}>
        <div className="grid grid-cols-2 gap-4">
          <Droppable droppableId="available">
            {(provided, snapshot) => (
              <div
                ref={provided.innerRef}
                {...provided.droppableProps}
                className={`border rounded-lg p-3 min-h-[200px] transition-colors ${
                  snapshot.isDraggingOver ? 'border-primary/50 bg-primary/5' : ''
                }`}
              >
                <h4 className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">
                  Available ({availableAgents.length})
                </h4>
                {availableAgents.map((agent, index) => (
                  <Draggable key={agent.id} draggableId={agent.id} index={index}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        {...provided.dragHandleProps}
                        className={`flex items-center gap-2 p-2 mb-1 rounded bg-muted text-sm transition-shadow ${
                          snapshot.isDragging ? 'shadow-md' : ''
                        }`}
                      >
                        <GripVertical className="size-3 text-muted-foreground shrink-0" />
                        <span className="truncate flex-1">{agent.name}</span>
                        <StatusBadge status={agent.status} size="sm" showLabel={false} />
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
                {availableAgents.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-4">
                    No available agents
                  </p>
                )}
              </div>
            )}
          </Droppable>

          <Droppable droppableId="assigned">
            {(provided, snapshot) => (
              <div
                ref={provided.innerRef}
                {...provided.droppableProps}
                className={`border border-dashed rounded-lg p-3 min-h-[200px] transition-colors ${
                  snapshot.isDraggingOver ? 'border-primary/50 bg-primary/5' : ''
                }`}
              >
                <h4 className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">
                  Assigned ({assignedMembers.length})
                </h4>
                {assignedMembers.map((m, index) => {
                  const info = agentLookup.get(m.agent_id!);
                  return (
                    <Draggable key={m.agent_id!} draggableId={m.agent_id!} index={index}>
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          {...provided.dragHandleProps}
                          className={`flex items-center gap-2 p-2 mb-1 rounded bg-primary/10 text-sm transition-shadow ${
                            snapshot.isDragging ? 'shadow-md' : ''
                          }`}
                        >
                          <GripVertical className="size-3 text-muted-foreground shrink-0" />
                          <span className="truncate flex-1">
                            {info?.name ?? m.agent_id}
                          </span>
                          {info && (
                            <StatusBadge status={info.status as AgentStatus} size="sm" showLabel={false} />
                          )}
                        </div>
                      )}
                    </Draggable>
                  );
                })}
                {provided.placeholder}
                {assignedMembers.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-4">
                    Drop agents here to add
                  </p>
                )}
              </div>
            )}
          </Droppable>
        </div>
      </DragDropContext>
    </div>
  );
}
