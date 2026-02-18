import { useState, useEffect, useCallback } from 'react';
import { Eye, EyeOff, Pencil, Trash2, Loader2 } from 'lucide-react';
import { getSecret } from '@/api/secrets';
import type { SecretSummary } from '@/types/secret';
import { TableCell, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

const REVEAL_DURATION_MS = 5000;

interface SecretRowProps {
  secret: SecretSummary;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
}

export function SecretRow({ secret, onEdit, onDelete }: SecretRowProps) {
  const [revealed, setRevealed] = useState(false);
  const [revealedValue, setRevealedValue] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Auto-hide after 5 seconds
  useEffect(() => {
    if (!revealed) return;
    const timer = setTimeout(() => {
      setRevealed(false);
      setRevealedValue(null);
    }, REVEAL_DURATION_MS);
    return () => clearTimeout(timer);
  }, [revealed]);

  const handleReveal = useCallback(async () => {
    if (revealed) {
      // Clicking EyeOff resets immediately
      setRevealed(false);
      setRevealedValue(null);
      return;
    }
    setLoading(true);
    try {
      const detail = await getSecret(secret.id);
      setRevealedValue(detail.value);
      setRevealed(true);
    } catch {
      // If fetch fails, stay hidden
    } finally {
      setLoading(false);
    }
  }, [revealed, secret.id]);

  return (
    <TableRow>
      <TableCell className="font-mono text-sm">{secret.key}</TableCell>
      <TableCell className="font-mono text-sm">
        {revealed && revealedValue !== null ? revealedValue : '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022'}
      </TableCell>
      <TableCell className="max-w-[200px] truncate text-muted-foreground text-sm">
        {secret.description ?? '\u2014'}
      </TableCell>
      <TableCell className="text-right">
        <div className="flex items-center justify-end gap-1">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => { void handleReveal(); }}
                disabled={loading}
              >
                {loading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : revealed ? (
                  <EyeOff className="size-4" />
                ) : (
                  <Eye className="size-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{revealed ? 'Hide value' : 'Reveal value'}</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => onEdit(secret.id)}
              >
                <Pencil className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Edit secret</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-8 text-destructive hover:text-destructive"
                onClick={() => onDelete(secret.id)}
              >
                <Trash2 className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Delete secret</TooltipContent>
          </Tooltip>
        </div>
      </TableCell>
    </TableRow>
  );
}
