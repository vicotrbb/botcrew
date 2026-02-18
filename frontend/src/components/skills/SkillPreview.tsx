import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';

interface SkillPreviewProps {
  content: string;
}

export function SkillPreview({ content }: SkillPreviewProps) {
  if (!content) {
    return (
      <div className="text-muted-foreground text-sm py-8 text-center">
        No content to preview
      </div>
    );
  }

  return <MarkdownRenderer content={content} />;
}
