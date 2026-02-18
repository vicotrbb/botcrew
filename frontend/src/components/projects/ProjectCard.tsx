import { Github, Calendar } from 'lucide-react';
import type { ProjectSummary } from '@/types/project';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

function formatDate(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return date.toLocaleDateString();
}

interface ProjectCardProps {
  project: ProjectSummary;
  agentCount?: number;
  onClick: () => void;
}

export function ProjectCard({ project, agentCount, onClick }: ProjectCardProps) {
  return (
    <Card
      className="p-4 cursor-pointer transition-all duration-200 hover:border-primary/50 hover:shadow-md"
      onClick={onClick}
      role="link"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium truncate block">{project.name}</span>
        <Badge variant="secondary" className="text-xs shrink-0">
          {project.status}
        </Badge>
      </div>

      {project.description && (
        <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
          {project.description}
        </p>
      )}

      <div className="mt-3 flex items-center gap-3 flex-wrap">
        {project.github_repo_url && (
          <Badge variant="outline" className="text-xs gap-1">
            <Github className="size-3" />
            GitHub
          </Badge>
        )}
        {agentCount !== undefined && (
          <span className="text-xs text-muted-foreground">
            {agentCount} {agentCount === 1 ? 'agent' : 'agents'}
          </span>
        )}
      </div>

      <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
        <Calendar className="size-3" />
        {formatDate(project.created_at)}
      </div>
    </Card>
  );
}
