import { useState } from 'react';
import { Plus, AlertCircle, RefreshCw, AlertTriangle, Loader2 } from 'lucide-react';
import { useSecrets, useDeleteSecret } from '@/hooks/use-secrets';
import { SecretsTable } from '@/components/secrets/SecretsTable';
import { SecretDialog } from '@/components/secrets/SecretDialog';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

function TableSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-2 py-3">
          <div className="h-4 w-32 bg-muted animate-pulse rounded" />
          <div className="h-4 w-24 bg-muted animate-pulse rounded" />
          <div className="h-4 w-48 bg-muted animate-pulse rounded flex-1" />
          <div className="h-4 w-24 bg-muted animate-pulse rounded" />
        </div>
      ))}
    </div>
  );
}

export function SecretsPage() {
  const { data: secrets, isLoading, error, refetch } = useSecrets();
  const deleteMutation = useDeleteSecret();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedSecretId, setSelectedSecretId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Find the secret being deleted by its ID
  const deleteTarget = deleteConfirmId
    ? secrets?.find((s) => s.id === deleteConfirmId)
    : null;

  function handleEdit(id: string) {
    setSelectedSecretId(id);
    setIsDialogOpen(true);
  }

  function handleCreate() {
    setSelectedSecretId(null);
    setIsDialogOpen(true);
  }

  function handleDelete(id: string) {
    setDeleteConfirmId(id);
  }

  function confirmDelete() {
    if (!deleteConfirmId) return;
    deleteMutation.mutate(deleteConfirmId, {
      onSuccess: () => setDeleteConfirmId(null),
    });
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Secrets</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage sensitive configuration accessible by agents
          </p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="size-4" />
          Add Secret
        </Button>
      </div>

      {isLoading && <TableSkeleton />}

      {error && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle className="size-8 text-destructive mb-3" />
          <p className="text-sm text-muted-foreground mb-4">
            Failed to load secrets. {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button variant="outline" size="sm" onClick={() => { void refetch(); }}>
            <RefreshCw className="size-4" />
            Retry
          </Button>
        </div>
      )}

      {secrets && (
        <Card>
          <SecretsTable
            secrets={secrets}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        </Card>
      )}

      {/* Create / Edit Dialog */}
      <SecretDialog
        secretId={selectedSecretId}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmId !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteConfirmId(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="size-5 text-destructive" />
              Delete Secret
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete{' '}
              <strong className="font-mono">{deleteTarget?.key ?? 'this secret'}</strong>?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete Secret'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
