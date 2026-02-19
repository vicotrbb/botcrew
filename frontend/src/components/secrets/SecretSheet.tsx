import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { createSecretSchema, updateSecretSchema } from '@/lib/schemas';
import type { CreateSecretInput, UpdateSecretInput } from '@/types/secret';
import { getSecret } from '@/api/secrets';
import { useCreateSecret, useUpdateSecret } from '@/hooks/use-secrets';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from '@/components/ui/sheet';
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

interface SecretSheetProps {
  secretId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SecretSheet({ secretId, open, onOpenChange }: SecretSheetProps) {
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
      void getSecret(secretId)
        .then((detail) => {
          form.reset({
            key: detail.key,
            value: detail.value,
            description: detail.description ?? '',
          });
          setLoadingSecret(false);
        })
        .catch(() => {
          toast.error('Something went wrong. Please try again.');
          setLoadingSecret(false);
          onOpenChange(false);
        });
    }
  }, [open, isEdit, secretId, form, onOpenChange]);

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
        onSuccess: () => {
          toast.success('Secret updated');
          onOpenChange(false);
        },
        onError: () => {
          toast.error('Something went wrong. Please try again.');
        },
      });
    } else {
      createMutation.mutate(data, {
        onSuccess: () => {
          toast.success('Secret created');
          onOpenChange(false);
        },
        onError: () => {
          toast.error('Something went wrong. Please try again.');
        },
      });
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-lg overflow-y-auto"
      >
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit Secret' : 'Create Secret'}</SheetTitle>
          <SheetDescription>
            {isEdit
              ? 'Update the secret key, value, or description.'
              : 'Add a new secret that agents can access.'}
          </SheetDescription>
        </SheetHeader>

        {loadingSecret ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="space-y-4 px-4"
            >
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

              <SheetFooter>
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
              </SheetFooter>
            </form>
          </Form>
        )}
      </SheetContent>
    </Sheet>
  );
}
