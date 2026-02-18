import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { createSecretSchema, updateSecretSchema } from '@/lib/schemas';
import type { CreateSecretInput, UpdateSecretInput } from '@/types/secret';
import { getSecret } from '@/api/secrets';
import { useCreateSecret, useUpdateSecret } from '@/hooks/use-secrets';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';

interface SecretDialogProps {
  secretId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SecretDialog({ secretId, open, onOpenChange }: SecretDialogProps) {
  const isEdit = secretId !== null;
  const [showValue, setShowValue] = useState(false);
  const [loadingSecret, setLoadingSecret] = useState(false);

  const createMutation = useCreateSecret();
  const updateMutation = useUpdateSecret(secretId ?? '');

  const form = useForm<CreateSecretInput>({
    resolver: zodResolver(isEdit ? updateSecretSchema : createSecretSchema),
    defaultValues: {
      key: '',
      value: '',
      description: '',
    },
  });

  // Fetch and populate form when editing
  useEffect(() => {
    if (!open) {
      form.reset({ key: '', value: '', description: '' });
      setShowValue(false);
      return;
    }

    if (isEdit && secretId) {
      setLoadingSecret(true);
      void getSecret(secretId).then((detail) => {
        form.reset({
          key: detail.key,
          value: detail.value,
          description: detail.description ?? '',
        });
        setLoadingSecret(false);
      }).catch(() => {
        setLoadingSecret(false);
      });
    }
  }, [open, isEdit, secretId, form]);

  function onSubmit(data: CreateSecretInput) {
    if (isEdit) {
      // Build partial update payload -- only send changed fields
      const dirtyFields = form.formState.dirtyFields;
      const patch: UpdateSecretInput = {};
      if (dirtyFields.key) patch.key = data.key;
      if (dirtyFields.value) patch.value = data.value;
      if (dirtyFields.description) patch.description = data.description;

      if (Object.keys(patch).length === 0) {
        onOpenChange(false);
        return;
      }

      updateMutation.mutate(patch, {
        onSuccess: () => onOpenChange(false),
      });
    } else {
      createMutation.mutate(data, {
        onSuccess: () => onOpenChange(false),
      });
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;
  const error = createMutation.error || updateMutation.error;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Secret' : 'Create Secret'}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Update the secret key, value, or description.'
              : 'Add a new secret that agents can access.'}
          </DialogDescription>
        </DialogHeader>

        {loadingSecret ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Key</FormLabel>
                    <FormControl>
                      <Input
                        className="font-mono"
                        placeholder="MY_SECRET_KEY"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="value"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Value</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showValue ? 'text' : 'password'}
                          placeholder="Secret value"
                          {...field}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="absolute right-0 top-0 size-9"
                          onClick={() => setShowValue((v) => !v)}
                        >
                          {showValue ? (
                            <EyeOff className="size-4" />
                          ) : (
                            <Eye className="size-4" />
                          )}
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description (optional)</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="What is this secret used for?"
                        rows={2}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {error && (
                <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                  {error.message}
                </div>
              )}

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isPending}>
                  {isPending ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      {isEdit ? 'Saving...' : 'Creating...'}
                    </>
                  ) : isEdit ? (
                    'Save Changes'
                  ) : (
                    'Create Secret'
                  )}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  );
}
