import type { ComponentPropsWithoutRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ShikiHighlighter, isInlineCode, rehypeInlineCodeProperty } from 'react-shiki/web';
import type { Element } from 'react-shiki/web';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

function CodeBlock({
  children,
  className,
  node,
  ...props
}: ComponentPropsWithoutRef<'code'> & { node?: Element }) {
  // Detect inline code: no parent <pre>, or node marks it inline
  const inline = node ? isInlineCode(node) : !className;

  if (inline) {
    return (
      <code
        className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono"
        {...props}
      >
        {children}
      </code>
    );
  }

  // Extract language from className like "language-typescript"
  const match = /language-(\w+)/.exec(className ?? '');
  const language = match?.[1] ?? 'text';
  const code = String(children).replace(/\n$/, '');

  return (
    <ShikiHighlighter
      language={language}
      theme={{ light: 'github-light', dark: 'github-dark' }}
      showLanguage={false}
    >
      {code}
    </ShikiHighlighter>
  );
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  if (!content) {
    return null;
  }

  return (
    <div className={`prose prose-sm dark:prose-invert max-w-none ${className ?? ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeInlineCodeProperty]}
        components={{
          code: CodeBlock,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
