/**
 * TokenRevealDialog — mostra il plaintext UNA volta sola dopo create/rotate.
 *
 * Pattern usato da AWS IAM access keys, GitHub PAT, Slack OAuth bot
 * tokens: il valore non è mai ri-leggibile dopo. Avviso esplicito.
 */

import { Copy } from 'lucide-react';
import { toast } from 'sonner';

import type { EmbedWithToken } from '../../../lib/api/embeds';
import { Button, ModalShell } from '../../ui';

interface Props {
  result: EmbedWithToken | null;
  onClose: () => void;
}

export function TokenRevealDialog({ result, onClose }: Props) {
  if (!result) return null;

  const origin = window.location.origin;
  const snippet = `<script src="${origin}/embed.js"
        data-token="${result.embed_token}"
        data-position="${result.theme.position ?? 'bottom-right'}"
        data-color="${result.theme.primary ?? '#0ea5e9'}"></script>`;

  const copyToken = async () => {
    try {
      await navigator.clipboard.writeText(result.embed_token);
      toast.success('Token copiato — incollalo subito in un password manager');
    } catch {
      toast.error('Copia fallita');
    }
  };

  const copySnippet = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      toast.success('Snippet copiato');
    } catch {
      toast.error('Copia fallita');
    }
  };

  return (
    <ModalShell open onClose={onClose} title={`Token "${result.name}"`} width="lg" blocking>
      <div className="space-y-4 p-1">
        <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <strong>Importante:</strong> il token plaintext viene mostrato UNA volta sola. Copialo
          ora — dopo questa schermata non sarà più recuperabile. Per emergenze usa "Ruota token".
        </div>

        <div>
          <div className="text-[11px] font-medium text-ink uppercase tracking-wide mb-1">
            Token (plaintext)
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              readOnly
              value={result.embed_token}
              onClick={(e) => (e.target as HTMLInputElement).select()}
              className="input-sm w-full font-mono"
            />
            <Button variant="primary" size="sm" onClick={() => void copyToken()}>
              <Copy size={13} />
              Copia
            </Button>
          </div>
        </div>

        <div>
          <div className="text-[11px] font-medium text-ink uppercase tracking-wide mb-1">
            Snippet HTML pronto da incollare
          </div>
          <pre className="rounded-md border border-[var(--color-border)] bg-zinc-50 p-3 font-mono text-[11px] leading-relaxed text-ink overflow-x-auto whitespace-pre-wrap">
            {snippet}
          </pre>
          <div className="mt-2 flex justify-end">
            <Button variant="secondary" size="sm" onClick={() => void copySnippet()}>
              <Copy size={13} />
              Copia snippet
            </Button>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <Button variant="primary" size="sm" onClick={onClose}>
            Ho copiato il token
          </Button>
        </div>
      </div>
    </ModalShell>
  );
}
