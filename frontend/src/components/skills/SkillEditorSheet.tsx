import { useState, useEffect, useCallback } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { markdown, markdownLanguage } from '@codemirror/lang-markdown';
import { languages } from '@codemirror/language-data';
import { githubLight, githubDark } from '@uiw/codemirror-theme-github';
import { Eye, Pencil, Trash2, Loader2 } from 'lucide-react';

import { useSkill, useCreateSkill, useUpdateSkill, useDeleteSkill } from '@/hooks/use-skills';
import type { CreateSkillInput, UpdateSkillInput } from '@/types/skill';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { SkillPreview } from './SkillPreview';

interface SkillEditorSheetProps {
  skillId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SkillEditorSheet({ skillId, open, onOpenChange }: SkillEditorSheetProps) {
  const isEditMode = !!skillId;

  // Fetch skill data when editing
  const { data: skill, isLoading: isLoadingSkill } = useSkill(skillId);

  // Mutations
  const createSkill = useCreateSkill();
  const updateSkill = useUpdateSkill(skillId ?? '');
  const deleteSkillMutation = useDeleteSkill();

  // Local form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [body, setBody] = useState('');
  const [isPreview, setIsPreview] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Track initial values for dirty detection
  const [initialName, setInitialName] = useState('');
  const [initialDescription, setInitialDescription] = useState('');
  const [initialBody, setInitialBody] = useState('');

  // Detect dark mode for CodeMirror theme
  const isDark = typeof window !== 'undefined' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches;

  // Initialize form state when skill data loads or when opening in create mode
  useEffect(() => {
    if (isEditMode && skill) {
      setName(skill.name);
      setDescription(skill.description);
      setBody(skill.body);
      setInitialName(skill.name);
      setInitialDescription(skill.description);
      setInitialBody(skill.body);
    } else if (!isEditMode && open) {
      setName('');
      setDescription('');
      setBody('');
      setInitialName('');
      setInitialDescription('');
      setInitialBody('');
    }
    setIsPreview(false);
  }, [skill, isEditMode, open]);

  const isDirty = name !== initialName || description !== initialDescription || body !== initialBody;

  const isSaving = createSkill.isPending || updateSkill.isPending;

  const handleSave = useCallback(() => {
    if (isEditMode && skillId) {
      // Build partial update with only changed fields
      const input: UpdateSkillInput = {};
      if (name !== initialName) input.name = name;
      if (description !== initialDescription) input.description = description;
      if (body !== initialBody) input.body = body;

      if (Object.keys(input).length === 0) return;

      updateSkill.mutate(input, {
        onSuccess: () => {
          onOpenChange(false);
        },
      });
    } else {
      const input: CreateSkillInput = { name, description, body };
      createSkill.mutate(input, {
        onSuccess: () => {
          onOpenChange(false);
        },
      });
    }
  }, [isEditMode, skillId, name, description, body, initialName, initialDescription, initialBody, updateSkill, createSkill, onOpenChange]);

  const handleDelete = useCallback(() => {
    if (!skillId) return;
    deleteSkillMutation.mutate(skillId, {
      onSuccess: () => {
        setShowDeleteDialog(false);
        onOpenChange(false);
      },
    });
  }, [skillId, deleteSkillMutation, onOpenChange]);

  const canSave = isEditMode
    ? isDirty && name.trim().length > 0 && description.trim().length > 0 && body.trim().length > 0
    : name.trim().length > 0 && description.trim().length > 0 && body.trim().length > 0;

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="right" className="w-full sm:max-w-3xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle>{isEditMode ? (skill?.name ?? 'Edit Skill') : 'New Skill'}</SheetTitle>
            <SheetDescription>
              {isEditMode ? 'Edit skill content and metadata' : 'Create a new skill with markdown content'}
            </SheetDescription>
          </SheetHeader>

          {isEditMode && isLoadingSkill ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="size-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="flex flex-col gap-4 px-4 pb-4">
              {/* Name field */}
              <div className="space-y-2">
                <Label htmlFor="skill-name">Name</Label>
                <Input
                  id="skill-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Skill name"
                  maxLength={100}
                />
              </div>

              {/* Description field */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="skill-description">Description</Label>
                  <span className="text-xs text-muted-foreground">{description.length}/250</span>
                </div>
                <Input
                  id="skill-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of this skill"
                  maxLength={250}
                />
              </div>

              {/* Editor/Preview toggle */}
              <div className="flex items-center gap-2">
                <Button
                  variant={isPreview ? 'outline' : 'default'}
                  size="sm"
                  onClick={() => setIsPreview(false)}
                >
                  <Pencil className="size-3.5" />
                  Edit
                </Button>
                <Button
                  variant={isPreview ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setIsPreview(true)}
                >
                  <Eye className="size-3.5" />
                  Preview
                </Button>
              </div>

              {/* Editor or Preview */}
              <div className="min-h-[400px] border rounded-md overflow-hidden">
                {isPreview ? (
                  <div className="p-4 h-[400px] overflow-y-auto">
                    <SkillPreview content={body} />
                  </div>
                ) : (
                  <CodeMirror
                    value={body}
                    height="400px"
                    theme={isDark ? githubDark : githubLight}
                    extensions={[
                      markdown({ base: markdownLanguage, codeLanguages: languages }),
                    ]}
                    onChange={(val) => setBody(val)}
                    placeholder="Write your skill instructions in markdown..."
                  />
                )}
              </div>

              {/* Action buttons */}
              <div className="flex items-center justify-between pt-2">
                <div>
                  {isEditMode && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setShowDeleteDialog(true)}
                    >
                      <Trash2 className="size-3.5" />
                      Delete
                    </Button>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" onClick={() => onOpenChange(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleSave} disabled={!canSave || isSaving}>
                    {isSaving && <Loader2 className="size-3.5 animate-spin" />}
                    {isEditMode ? 'Save Changes' : 'Create Skill'}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Delete confirmation dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Skill</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{skill?.name}&quot;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteSkillMutation.isPending}
            >
              {deleteSkillMutation.isPending && <Loader2 className="size-3.5 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
