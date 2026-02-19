import { DragDropContext, Droppable, Draggable, type DropResult } from '@hello-pangea/dnd';
import { GripVertical } from 'lucide-react';
import { toast } from 'sonner';
import { useAgents } from '@/hooks/use-agents';
import { useProjectAgents, useAssignAgent, useRemoveAgent } from '@/hooks/use-projects';
import { StatusBadge } from '@/components/shared/StatusBadge';
import type { AgentStatus } from '@/types/agent';

interface AgentAssignmentProps {
  projectId: string;
}

export function AgentAssignment({ projectId }: AgentAssignmentProps) {
  const { data: allAgents, isLoading: agentsLoading } = useAgents();
  const { data: projectAgents, isLoading: assignmentsLoading } = useProjectAgents(projectId);
  const assignAgent = useAssignAgent(projectId);
  const removeAgent = useRemoveAgent(projectId);

  const isLoading = agentsLoading || assignmentsLoading;

  // Build set of assigned agent IDs for filtering
  const assignedAgentIds = new Set(projectAgents?.map((pa) => pa.agent_id) ?? []);

  // Available agents = all agents minus assigned
  const availableAgents = (allAgents ?? []).filter((a) => !assignedAgentIds.has(a.id));

  // Build a lookup for agent names/status from allAgents
  const agentLookup = new Map(
    (allAgents ?? []).map((a) => [a.id, { name: a.name, status: a.status }]),
  );

  function handleDragEnd(result: DropResult) {
    if (!result.destination) return;
    const { source, destination, draggableId } = result;

    if (source.droppableId === 'available' && destination.droppableId === 'assigned') {
      assignAgent.mutate(
        { agent_id: draggableId },
        {
          onSuccess: () => {
            toast.success('Agent assigned to project');
          },
          onError: () => {
            toast.error('Something went wrong. Please try again.');
          },
        },
      );
    } else if (source.droppableId === 'assigned' && destination.droppableId === 'available') {
      // draggableId for assigned items is the agent_id
      removeAgent.mutate(draggableId, {
        onSuccess: () => {
          toast.success('Agent removed from project');
        },
        onError: () => {
          toast.error('Something went wrong. Please try again.');
        },
      });
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-medium">Agent Assignment</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="border rounded-lg p-3 min-h-[200px] bg-muted/30 animate-pulse" />
          <div className="border rounded-lg p-3 min-h-[200px] bg-muted/30 animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">Agent Assignment</h3>
      <p className="text-xs text-muted-foreground mb-2">
        Drag agents between lists to assign or remove them from this project.
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
                  Assigned ({projectAgents?.length ?? 0})
                </h4>
                {(projectAgents ?? []).map((pa, index) => {
                  const info = agentLookup.get(pa.agent_id);
                  return (
                    <Draggable key={pa.agent_id} draggableId={pa.agent_id} index={index}>
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
                            {info?.name ?? pa.agent_id}
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
                {(projectAgents?.length ?? 0) === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-4">
                    Drop agents here to assign
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
