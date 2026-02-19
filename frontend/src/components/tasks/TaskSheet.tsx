import { useState, useEffect } from 'react';
import { useForm, Controller, type Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import CodeMirror from '@uiw/react-codemirror';
import { markdown, markdownLanguage } from '@codemirror/lang-markdown';
import { languages } from '@codemirror/language-data';
import { githubLight, githubDark } from '@uiw/codemirror-theme-github';
import { Loader2, Trash2, AlertTriangle, X, Plus } from 'lucide-react';
import { toast } from 'sonner';

import { createTaskSchema, updateTaskSchema } from '@/lib/schemas';
import type { CreateTaskFormInput, UpdateTaskFormInput } from '@/lib/schemas';
import {
  useTask,
  useCreateTask,
  useUpdateTask,
  useDeleteTask,
  useTaskSecrets,
  useAssignTaskSecret,
  useRemoveTaskSecret,
  useTaskSkills,
  useAssignTaskSkill,
  useRemoveTaskSkill,
} from '@/hooks/use-tasks';
import { useSecrets } from '@/hooks/use-secrets';
import { useSkills } from '@/hooks/use-skills';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { TaskAgentAssignment } from './TaskAgentAssignment';

interface TaskSheetProps {
  taskId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TaskSheet({ taskId, open, onOpenChange }: TaskSheetProps) {
  const isEdit = taskId !== null;

  // Data hooks (edit mode only)
  const { data: task, isLoading: isLoadingTask } = useTask(taskId);

  // Mutations
  const createMutation = useCreateTask();
  const updateMutation = useUpdateTask(taskId ?? '');
  const deleteMutation = useDeleteTask();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Detect dark mode for CodeMirror theme
  const isDark =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches;

  // Form for create mode
  const createForm = useForm<CreateTaskFormInput>({
    resolver: zodResolver(createTaskSchema),
    defaultValues: {
      name: '',
      description: '',
      directive: '',
    },
  });

  // Form for edit mode
  const editForm = useForm<UpdateTaskFormInput>({
    resolver: zodResolver(updateTaskSchema) as Resolver<UpdateTaskFormInput>,
    defaultValues: {
      name: '',
      description: '',
      directive: '',
      status: 'open',
    },
  });

  // Reset create form on open/close
  useEffect(() => {
    if (!open) {
      createForm.reset({ name: '', description: '', directive: '' });
    }
  }, [open, createForm]);

  // Populate edit form when task data loads
  useEffect(() => {
    if (isEdit && task) {
      editForm.reset({
        name: task.name,
        description: task.description ?? '',
        directive: task.directive,
        status: task.status as 'open' | 'done',
      });
    }
  }, [isEdit, task, editForm]);

  function handleCreate(data: CreateTaskFormInput) {
    createMutation.mutate(
      {
        name: data.name,
        description: data.description || undefined,
        directive: data.directive,
      },
      {
        onSuccess: () => {
          toast.success('Task created');
          onOpenChange(false);
        },
        onError: () => {
          toast.error('Something went wrong. Please try again.');
        },
      },
    );
  }

  function handleUpdate(data: UpdateTaskFormInput) {
    const dirtyFields = editForm.formState.dirtyFields;
    const patch: UpdateTaskFormInput = {};
    if (dirtyFields.name) patch.name = data.name;
    if (dirtyFields.description) patch.description = data.description;
    if (dirtyFields.directive) patch.directive = data.directive;
    if (dirtyFields.status) patch.status = data.status;

    if (Object.keys(patch).length === 0) {
      onOpenChange(false);
      return;
    }

    updateMutation.mutate(patch, {
      onSuccess: () => {
        toast.success('Task updated');
        onOpenChange(false);
      },
      onError: () => {
        toast.error('Something went wrong. Please try again.');
      },
    });
  }

  function handleDelete() {
    if (!taskId) return;
    deleteMutation.mutate(taskId, {
      onSuccess: () => {
        toast.success('Task deleted');
        setDeleteDialogOpen(false);
        onOpenChange(false);
      },
      onError: () => {
        toast.error('Something went wrong. Please try again.');
      },
    });
  }

  const isPending =
    createMutation.isPending || updateMutation.isPending;

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent
          side="right"
          className="w-full sm:max-w-2xl overflow-y-auto"
        >
          <SheetHeader>
            <SheetTitle>{isEdit ? 'Task Details' : 'Create Task'}</SheetTitle>
            <SheetDescription>
              {isEdit
                ? 'View and edit task configuration, assignments, and notes.'
                : 'Create a new task with a name, description, and directive.'}
            </SheetDescription>
          </SheetHeader>

          {/* Loading state for edit mode */}
          {isEdit && isLoadingTask && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="size-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Create mode */}
          {!isEdit && (
            <Form {...createForm}>
              <form
                onSubmit={createForm.handleSubmit(handleCreate)}
                className="space-y-4 px-4"
              >
                <FormField
                  control={createForm.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Name</FormLabel>
                      <FormControl>
                        <Input placeholder="Task name" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={createForm.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Description (optional)</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="Brief description of this task"
                          rows={2}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={createForm.control}
                  name="directive"
                  render={() => (
                    <FormItem>
                      <FormLabel>Directive</FormLabel>
                      <FormControl>
                        <Controller
                          control={createForm.control}
                          name="directive"
                          render={({ field }) => (
                            <div className="min-h-[200px] border rounded-md overflow-hidden">
                              <CodeMirror
                                value={field.value}
                                height="200px"
                                theme={isDark ? githubDark : githubLight}
                                extensions={[
                                  markdown({
                                    base: markdownLanguage,
                                    codeLanguages: languages,
                                  }),
                                ]}
                                onChange={(val) => field.onChange(val)}
                                placeholder="Write your task directive in markdown..."
                              />
                            </div>
                          )}
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
                        Creating...
                      </>
                    ) : (
                      'Create Task'
                    )}
                  </Button>
                </SheetFooter>
              </form>
            </Form>
          )}

          {/* Edit mode */}
          {isEdit && task && (
            <div className="space-y-6 px-4 pb-6">
              <Form {...editForm}>
                <form
                  onSubmit={editForm.handleSubmit(handleUpdate)}
                  className="space-y-4"
                >
                  <FormField
                    control={editForm.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Task name" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={editForm.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description (optional)</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Brief description of this task"
                            rows={2}
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={editForm.control}
                    name="directive"
                    render={() => (
                      <FormItem>
                        <FormLabel>Directive</FormLabel>
                        <FormControl>
                          <Controller
                            control={editForm.control}
                            name="directive"
                            render={({ field }) => (
                              <div className="min-h-[200px] border rounded-md overflow-hidden">
                                <CodeMirror
                                  value={field.value ?? ''}
                                  height="200px"
                                  theme={isDark ? githubDark : githubLight}
                                  extensions={[
                                    markdown({
                                      base: markdownLanguage,
                                      codeLanguages: languages,
                                    }),
                                  ]}
                                  onChange={(val) => field.onChange(val)}
                                  placeholder="Write your task directive in markdown..."
                                />
                              </div>
                            )}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={editForm.control}
                    name="status"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Status</FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          value={field.value}
                        >
                          <FormControl>
                            <SelectTrigger className="w-full">
                              <SelectValue placeholder="Select status" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="open">Open</SelectItem>
                            <SelectItem value="done">Done</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="flex justify-end">
                    <Button type="submit" disabled={isPending}>
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

              <Separator />

              {/* Agent Assignment */}
              <TaskAgentAssignment taskId={taskId} />

              <Separator />

              {/* Secret Assignment */}
              <SecretAssignmentSection taskId={taskId} />

              <Separator />

              {/* Skill Assignment */}
              <SkillAssignmentSection taskId={taskId} />

              {/* Notes (read-only) */}
              {task.notes && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium">Notes</h3>
                    <div className="border rounded-md p-3 bg-muted/30 max-h-[300px] overflow-y-auto">
                      <MarkdownRenderer content={task.notes} />
                    </div>
                  </div>
                </>
              )}

              <Separator />

              {/* Delete */}
              <div className="flex justify-end">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setDeleteDialogOpen(true)}
                >
                  <Trash2 className="size-4" />
                  Delete Task
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="size-5 text-destructive" />
              Delete Task
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete{' '}
              <strong>{task?.name}</strong>? This will remove the task and all
              its assignments. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete Task'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// --- Secret Assignment Sub-component ---

function SecretAssignmentSection({ taskId }: { taskId: string }) {
  const { data: taskSecrets, isLoading: secretsLoading } = useTaskSecrets(taskId);
  const { data: allSecrets } = useSecrets();
  const assignSecret = useAssignTaskSecret(taskId);
  const removeSecret = useRemoveTaskSecret(taskId);
  const [addOpen, setAddOpen] = useState(false);

  const assignedSecretIds = new Set(taskSecrets?.map((ts) => ts.secret_id) ?? []);
  const availableSecrets = (allSecrets ?? []).filter((s) => !assignedSecretIds.has(s.id));

  // Build lookup for secret key by id
  const secretLookup = new Map(
    (allSecrets ?? []).map((s) => [s.id, s.key]),
  );

  function handleAssignSecret(secretId: string) {
    assignSecret.mutate(
      { secret_id: secretId },
      {
        onSuccess: () => {
          toast.success('Secret assigned to task');
          setAddOpen(false);
        },
        onError: () => {
          toast.error('Something went wrong. Please try again.');
        },
      },
    );
  }

  function handleRemoveSecret(secretId: string) {
    removeSecret.mutate(secretId, {
      onSuccess: () => {
        toast.success('Secret removed from task');
      },
      onError: () => {
        toast.error('Something went wrong. Please try again.');
      },
    });
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Assigned Secrets</h3>
        {availableSecrets.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAddOpen(!addOpen)}
          >
            <Plus className="size-3.5" />
            Add
          </Button>
        )}
      </div>

      {addOpen && availableSecrets.length > 0 && (
        <Select onValueChange={handleAssignSecret}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select a secret to assign" />
          </SelectTrigger>
          <SelectContent>
            {availableSecrets.map((secret) => (
              <SelectItem key={secret.id} value={secret.id}>
                {secret.key}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {secretsLoading ? (
        <div className="h-8 bg-muted/30 animate-pulse rounded" />
      ) : (taskSecrets ?? []).length === 0 ? (
        <p className="text-xs text-muted-foreground">No secrets assigned.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {(taskSecrets ?? []).map((ts) => (
            <Badge key={ts.id} variant="secondary" className="gap-1 pr-1">
              <span className="font-mono text-xs">
                {secretLookup.get(ts.secret_id) ?? ts.secret_id}
              </span>
              <button
                type="button"
                onClick={() => handleRemoveSecret(ts.secret_id)}
                className="ml-1 rounded-sm p-0.5 hover:bg-muted transition-colors"
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Skill Assignment Sub-component ---

function SkillAssignmentSection({ taskId }: { taskId: string }) {
  const { data: taskSkills, isLoading: skillsLoading } = useTaskSkills(taskId);
  const { data: allSkills } = useSkills();
  const assignSkill = useAssignTaskSkill(taskId);
  const removeSkill = useRemoveTaskSkill(taskId);
  const [addOpen, setAddOpen] = useState(false);

  const assignedSkillIds = new Set(taskSkills?.map((ts) => ts.skill_id) ?? []);
  const availableSkills = (allSkills ?? []).filter((s) => !assignedSkillIds.has(s.id));

  // Build lookup for skill name by id
  const skillLookup = new Map(
    (allSkills ?? []).map((s) => [s.id, s.name]),
  );

  function handleAssignSkill(skillId: string) {
    assignSkill.mutate(
      { skill_id: skillId },
      {
        onSuccess: () => {
          toast.success('Skill assigned to task');
          setAddOpen(false);
        },
        onError: () => {
          toast.error('Something went wrong. Please try again.');
        },
      },
    );
  }

  function handleRemoveSkill(skillId: string) {
    removeSkill.mutate(skillId, {
      onSuccess: () => {
        toast.success('Skill removed from task');
      },
      onError: () => {
        toast.error('Something went wrong. Please try again.');
      },
    });
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Assigned Skills</h3>
        {availableSkills.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAddOpen(!addOpen)}
          >
            <Plus className="size-3.5" />
            Add
          </Button>
        )}
      </div>

      {addOpen && availableSkills.length > 0 && (
        <Select onValueChange={handleAssignSkill}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select a skill to assign" />
          </SelectTrigger>
          <SelectContent>
            {availableSkills.map((skill) => (
              <SelectItem key={skill.id} value={skill.id}>
                {skill.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {skillsLoading ? (
        <div className="h-8 bg-muted/30 animate-pulse rounded" />
      ) : (taskSkills ?? []).length === 0 ? (
        <p className="text-xs text-muted-foreground">No skills assigned.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {(taskSkills ?? []).map((ts) => (
            <Badge key={ts.id} variant="secondary" className="gap-1 pr-1">
              <span className="text-xs">
                {skillLookup.get(ts.skill_id) ?? ts.skill_id}
              </span>
              <button
                type="button"
                onClick={() => handleRemoveSkill(ts.skill_id)}
                className="ml-1 rounded-sm p-0.5 hover:bg-muted transition-colors"
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
