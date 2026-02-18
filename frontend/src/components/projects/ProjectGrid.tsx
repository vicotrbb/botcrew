import { FolderKanban } from 'lucide-react';
import type { ProjectSummary } from '@/types/project';
import { ProjectCard } from './ProjectCard';

interface ProjectGridProps {
  projects: ProjectSummary[];
  onSelectProject: (id: string) => void;
}

export function ProjectGrid({ projects, onSelectProject }: ProjectGridProps) {
  if (projects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <FolderKanban className="size-12 text-muted-foreground mb-3" />
        <p className="text-muted-foreground text-sm">No projects yet.</p>
        <p className="text-muted-foreground text-sm mt-1">
          Create your first project to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {projects.map((project) => (
        <ProjectCard
          key={project.id}
          project={project}
          onClick={() => onSelectProject(project.id)}
        />
      ))}
    </div>
  );
}
