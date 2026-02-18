import { useState } from 'react';
import { Plus, AlertCircle, RefreshCw } from 'lucide-react';
import { useSkills } from '@/hooks/use-skills';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
import { SkillsTable } from '@/components/skills/SkillsTable';
import { SkillEditorSheet } from '@/components/skills/SkillEditorSheet';

function SkillsTableSkeleton() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Description</TableHead>
          <TableHead>Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: 5 }).map((_, i) => (
          <TableRow key={i}>
            <TableCell>
              <div className="h-4 w-24 bg-muted animate-pulse rounded" />
            </TableCell>
            <TableCell>
              <div className="h-4 w-48 bg-muted animate-pulse rounded" />
            </TableCell>
            <TableCell>
              <div className="h-4 w-20 bg-muted animate-pulse rounded" />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function SkillsPage() {
  const { data, isLoading, error, refetch } = useSkills();
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);

  function handleCreateSkill() {
    setSelectedSkillId(null);
    setIsEditorOpen(true);
  }

  function handleSelectSkill(id: string) {
    setSelectedSkillId(id);
    setIsEditorOpen(true);
  }

  function handleEditorOpenChange(open: boolean) {
    setIsEditorOpen(open);
    if (!open) {
      setSelectedSkillId(null);
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Skills</h1>
          <p className="text-muted-foreground text-sm mt-1">Manage your skills library</p>
        </div>
        <Button onClick={handleCreateSkill}>
          <Plus className="size-4" />
          Create Skill
        </Button>
      </div>

      {isLoading && <SkillsTableSkeleton />}

      {error && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle className="size-8 text-destructive mb-3" />
          <p className="text-sm text-muted-foreground mb-4">
            Failed to load skills. {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button variant="outline" size="sm" onClick={() => { void refetch(); }}>
            <RefreshCw className="size-4" />
            Retry
          </Button>
        </div>
      )}

      {data && <SkillsTable skills={data} onSelectSkill={handleSelectSkill} />}

      <SkillEditorSheet
        skillId={selectedSkillId}
        open={isEditorOpen}
        onOpenChange={handleEditorOpenChange}
      />
    </div>
  );
}
