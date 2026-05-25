import { ImagePlus, Loader2, Save, X } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { uploadTenantLogo } from '../../../lib/api/admin';
import { Button, IconButton } from '../../ui';
import { SubHeader } from './atoms';

interface Props {
  tenant: string;
  onUploaded: () => void;
}

export function BrandingLogoPanel({ tenant, onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    setBusy(true);
    try {
      await uploadTenantLogo(tenant, file);
      setFile(null);
      onUploaded();
      toast.success('Logo aggiornato.');
    } catch (e) {
      toast.error(`Upload logo fallito: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-3">
      <SubHeader title="Logo" icon={ImagePlus} />
      <label
        className="focus-ring inline-flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-[var(--color-border)]
                   px-3 py-2 text-[11px] font-medium hover:border-[var(--color-brand-ring)] hover:bg-[var(--color-canvas-raised)]"
      >
        <input
          type="file"
          accept=".png,.jpg,.jpeg,.webp"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            if (!f) return;
            if (f.size > 2 * 1024 * 1024) {
              toast.error('Logo > 2 MB.');
              return;
            }
            setFile(f);
          }}
        />
        <ImagePlus size={13} className="text-[var(--color-brand)]" aria-hidden />
        {file ? file.name : 'Seleziona file · PNG / JPG / WEBP · max 2 MB'}
      </label>
      {file && (
        <div className="flex items-center gap-2">
          <IconButton icon={X} aria-label="rimuovi" size="sm" onClick={() => setFile(null)} />
          <Button
            variant="primary"
            onClick={handleUpload}
            disabled={busy}
            className="!text-[11px]"
          >
            {busy ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
            Carica logo
          </Button>
        </div>
      )}
    </div>
  );
}
