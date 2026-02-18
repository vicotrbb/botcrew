import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2 } from 'lucide-react';
import {
  createProjectSchema,
  updateProjectSchema,
  type CreateProjectFormInput,
  type UpdateProjectFormInput,
} from '@/lib/schemas';
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';

interface CreateFormProps {
  mode: 'create';
  onSubmit: (data: CreateProjectFormInput) => void;
  isPending: boolean;
  error?: Error | null;
}

interface EditFormProps {
  mode: 'edit';
  defaultValues: UpdateProjectFormInput;
  onSubmit: (data: UpdateProjectFormInput) => void;
  isPending: boolean;
  error?: Error | null;
}

type ProjectFormProps = CreateFormProps | EditFormProps;

export function ProjectForm(props: ProjectFormProps) {
  if (props.mode === 'create') {
    return <CreateForm {...props} />;
  }
  return <EditForm {...props} />;
}

function CreateForm({ onSubmit, isPending, error }: CreateFormProps) {
  const form = useForm<CreateProjectFormInput>({
    resolver: zodResolver(createProjectSchema),
    defaultValues: {
      name: '',
      description: '',
      goals: '',
      github_repo_url: '',
    },
  });

  function handleSubmit(data: CreateProjectFormInput) {
    // Strip empty optional strings
    const payload: CreateProjectFormInput = {
      name: data.name,
      ...(data.description ? { description: data.description } : {}),
      ...(data.goals ? { goals: data.goals } : {}),
      ...(data.github_repo_url ? { github_repo_url: data.github_repo_url } : {}),
    };
    onSubmit(payload);
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="My Project" {...field} />
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
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Brief description of the project..."
                  rows={2}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="goals"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Goals</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Project goals and objectives..."
                  rows={3}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="github_repo_url"
          render={({ field }) => (
            <FormItem>
              <FormLabel>GitHub Repository URL</FormLabel>
              <FormControl>
                <Input
                  placeholder="https://github.com/org/repo"
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

        <Button type="submit" className="w-full" disabled={isPending}>
          {isPending ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Creating...
            </>
          ) : (
            'Create Project'
          )}
        </Button>
      </form>
    </Form>
  );
}

function EditForm({ defaultValues, onSubmit, isPending, error }: EditFormProps) {
  const form = useForm<UpdateProjectFormInput>({
    resolver: zodResolver(updateProjectSchema),
    defaultValues,
  });

  function handleSubmit(data: UpdateProjectFormInput) {
    // Only send dirty fields
    const dirtyFields = form.formState.dirtyFields;
    const changedData: Partial<UpdateProjectFormInput> = {};
    for (const key of Object.keys(dirtyFields) as (keyof UpdateProjectFormInput)[]) {
      if (dirtyFields[key]) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (changedData as any)[key] = data[key];
      }
    }

    if (Object.keys(changedData).length === 0) return;

    // Convert empty github_repo_url to null for the API
    if (changedData.github_repo_url === '') {
      changedData.github_repo_url = undefined;
    }

    onSubmit(changedData as UpdateProjectFormInput);
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input {...field} />
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
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea rows={2} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="goals"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Goals</FormLabel>
              <FormControl>
                <Textarea rows={3} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="specs"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Specs</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Technical specifications..."
                  rows={4}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="github_repo_url"
          render={({ field }) => (
            <FormItem>
              <FormLabel>GitHub Repository URL</FormLabel>
              <FormControl>
                <Input
                  placeholder="https://github.com/org/repo"
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

        <div className="flex justify-end">
          <Button
            type="submit"
            disabled={!form.formState.isDirty || isPending}
          >
            {isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </Button>
        </div>
      </form>
    </Form>
  );
}
