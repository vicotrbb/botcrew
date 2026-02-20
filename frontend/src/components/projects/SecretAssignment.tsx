import { DragDropContext, Droppable, Draggable, type DropResult } from '@hello-pangea/dnd';
import { GripVertical } from 'lucide-react';
import { toast } from 'sonner';
import { useSecrets } from '@/hooks/use-secrets';
import { useProjectSecrets, useAssignSecret, useRemoveSecret } from '@/hooks/use-projects';

interface SecretAssignmentProps {
  projectId: string;
}

export function SecretAssignment({ projectId }: SecretAssignmentProps) {
  const { data: allSecrets, isLoading: secretsLoading } = useSecrets();
  const { data: projectSecrets, isLoading: assignmentsLoading } = useProjectSecrets(projectId);
  const assignSecret = useAssignSecret(projectId);
  const removeSecret = useRemoveSecret(projectId);

  const isLoading = secretsLoading || assignmentsLoading;

  // Build set of assigned secret IDs for filtering
  const assignedSecretIds = new Set(projectSecrets?.map((ps) => ps.secret_id) ?? []);

  // Available secrets = all secrets minus assigned
  const availableSecrets = (allSecrets ?? []).filter((s) => !assignedSecretIds.has(s.id));

  // Build a lookup for secret key names
  const secretLookup = new Map(
    (allSecrets ?? []).map((s) => [s.id, s.key]),
  );

  function handleDragEnd(result: DropResult) {
    if (!result.destination) return;
    const { source, destination, draggableId } = result;

    if (source.droppableId === 'available' && destination.droppableId === 'assigned') {
      assignSecret.mutate(
        { secret_id: draggableId },
        {
          onSuccess: () => {
            toast.success('Secret assigned to project');
          },
          onError: () => {
            toast.error('Something went wrong. Please try again.');
          },
        },
      );
    } else if (source.droppableId === 'assigned' && destination.droppableId === 'available') {
      removeSecret.mutate(draggableId, {
        onSuccess: () => {
          toast.success('Secret removed from project');
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
        <h3 className="text-sm font-medium">Secret Assignment</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="border rounded-lg p-3 min-h-[200px] bg-muted/30 animate-pulse" />
          <div className="border rounded-lg p-3 min-h-[200px] bg-muted/30 animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">Secret Assignment</h3>
      <p className="text-xs text-muted-foreground mb-2">
        Drag secrets between lists to assign or remove them from this project.
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
                  Available ({availableSecrets.length})
                </h4>
                {availableSecrets.map((secret, index) => (
                  <Draggable key={secret.id} draggableId={secret.id} index={index}>
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
                        <span className="truncate flex-1">{secret.key}</span>
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
                {availableSecrets.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-4">
                    No available secrets
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
                  Assigned ({projectSecrets?.length ?? 0})
                </h4>
                {(projectSecrets ?? []).map((ps, index) => {
                  const keyName = secretLookup.get(ps.secret_id);
                  return (
                    <Draggable key={ps.secret_id} draggableId={ps.secret_id} index={index}>
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
                            {keyName ?? ps.secret_id}
                          </span>
                        </div>
                      )}
                    </Draggable>
                  );
                })}
                {provided.placeholder}
                {(projectSecrets?.length ?? 0) === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-4">
                    Drop secrets here to assign
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
