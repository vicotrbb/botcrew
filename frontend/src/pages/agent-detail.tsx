import { useParams } from 'react-router';

export function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Agent Detail</h1>
      <p className="text-muted-foreground mt-1">Agent ID: {id}</p>
      {/* Detail/edit form will be added by Plan 05 */}
    </div>
  );
}
