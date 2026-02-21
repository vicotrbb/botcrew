import { useState } from 'react';
import {
  Loader2,
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  File,
  ChevronRight,
  ChevronDown,
  X,
} from 'lucide-react';
import { useWorkspaceTree, useWorkspaceFileContent } from '@/hooks/use-projects';
import type { WorkspaceTreeNode } from '@/types/project';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';

const CODE_EXTENSIONS = new Set([
  'ts', 'tsx', 'js', 'jsx', 'py', 'go', 'rs', 'rb', 'java', 'c', 'cpp',
  'h', 'hpp', 'css', 'scss', 'html', 'json', 'yaml', 'yml', 'toml',
  'sh', 'bash', 'zsh', 'sql', 'graphql', 'vue', 'svelte',
]);

const TEXT_EXTENSIONS = new Set([
  'md', 'txt', 'csv', 'log', 'env', 'gitignore', 'dockerignore',
  'editorconfig', 'prettierrc', 'eslintrc',
]);

function getExtension(name: string): string {
  const parts = name.split('.');
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
}

function FileIcon({ name }: { name: string }) {
  const ext = getExtension(name);
  if (CODE_EXTENSIONS.has(ext)) return <FileCode className="size-4 shrink-0 text-blue-500" />;
  if (TEXT_EXTENSIONS.has(ext)) return <FileText className="size-4 shrink-0 text-muted-foreground" />;
  return <File className="size-4 shrink-0 text-muted-foreground" />;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface TreeNodeProps {
  node: WorkspaceTreeNode;
  depth: number;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
}

function TreeNode({ node, depth, selectedPath, onSelectFile }: TreeNodeProps) {
  const [open, setOpen] = useState(depth < 2);

  if (node.type === 'file') {
    const isSelected = node.path === selectedPath;
    return (
      <button
        className={`flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-sm hover:bg-accent ${
          isSelected ? 'bg-accent font-medium' : ''
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => node.path && onSelectFile(node.path)}
      >
        <FileIcon name={node.name} />
        <span className="truncate">{node.name}</span>
        {node.size !== undefined && (
          <span className="ml-auto shrink-0 text-xs text-muted-foreground">
            {formatFileSize(node.size)}
          </span>
        )}
      </button>
    );
  }

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button
          className="flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-sm hover:bg-accent"
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
        >
          {open ? (
            <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
          )}
          {open ? (
            <FolderOpen className="size-4 shrink-0 text-amber-500" />
          ) : (
            <Folder className="size-4 shrink-0 text-amber-500" />
          )}
          <span className="truncate">{node.name}</span>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        {node.children?.map((child, i) => (
          <TreeNode
            key={child.name + i}
            node={child}
            depth={depth + 1}
            selectedPath={selectedPath}
            onSelectFile={onSelectFile}
          />
        ))}
      </CollapsibleContent>
    </Collapsible>
  );
}

function FileContentViewer({
  projectId,
  filePath,
  onClose,
}: {
  projectId: string;
  filePath: string;
  onClose: () => void;
}) {
  const { data, isLoading, error } = useWorkspaceFileContent(projectId, filePath);

  return (
    <div className="rounded-md border">
      <div className="flex items-center justify-between border-b bg-muted/50 px-3 py-2">
        <span className="truncate text-sm font-medium">{filePath}</span>
        <Button variant="ghost" size="icon" className="size-6" onClick={onClose}>
          <X className="size-3.5" />
        </Button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
        </div>
      )}

      {error && (
        <div className="px-3 py-4 text-sm text-destructive">
          Failed to load file content.
        </div>
      )}

      {data && (
        <div className="max-h-[400px] overflow-auto">
          {data.is_binary ? (
            <div className="px-3 py-4 text-sm text-muted-foreground">
              Binary file ({formatFileSize(data.size)}) — cannot display content.
            </div>
          ) : data.content === null ? (
            <div className="px-3 py-4 text-sm text-muted-foreground">
              File too large to display ({formatFileSize(data.size)}).
            </div>
          ) : getExtension(filePath) === 'md' ? (
            <div className="p-3">
              <MarkdownRenderer content={data.content} />
            </div>
          ) : (
            <pre className="p-3 text-xs leading-relaxed">
              <code>{data.content}</code>
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

interface FileExplorerProps {
  projectId: string;
}

export function FileExplorer({ projectId }: FileExplorerProps) {
  const { data, isLoading, error } = useWorkspaceTree(projectId);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold">Workspace Files</h3>

      {isLoading && (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
        </div>
      )}

      {error && (
        <p className="text-sm text-muted-foreground">
          No workspace files available.
        </p>
      )}

      {data?.tree && (
        <ScrollArea className="max-h-[300px] rounded-md border">
          <div className="py-1">
            {data.tree.children?.length ? (
              data.tree.children.map((child, i) => (
                <TreeNode
                  key={child.name + i}
                  node={child}
                  depth={0}
                  selectedPath={selectedFile}
                  onSelectFile={setSelectedFile}
                />
              ))
            ) : (
              <p className="px-3 py-4 text-sm text-muted-foreground">
                Workspace directory is empty.
              </p>
            )}
          </div>
        </ScrollArea>
      )}

      {selectedFile && (
        <FileContentViewer
          projectId={projectId}
          filePath={selectedFile}
          onClose={() => setSelectedFile(null)}
        />
      )}
    </div>
  );
}
