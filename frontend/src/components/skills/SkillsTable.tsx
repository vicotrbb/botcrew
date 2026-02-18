import type { SkillSummary } from '@/types/skill';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';

interface SkillsTableProps {
  skills: SkillSummary[];
  onSelectSkill: (id: string) => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function SkillsTable({ skills, onSelectSkill }: SkillsTableProps) {
  if (skills.length === 0) {
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
          <TableRow>
            <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
              No skills yet
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
  }

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
        {skills.map((skill) => (
          <TableRow
            key={skill.id}
            className="cursor-pointer"
            onClick={() => onSelectSkill(skill.id)}
          >
            <TableCell className="font-medium">{skill.name}</TableCell>
            <TableCell className="text-muted-foreground max-w-[300px] truncate">
              {skill.description}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {formatDate(skill.updated_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
