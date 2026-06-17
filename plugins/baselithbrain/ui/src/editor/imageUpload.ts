import type { Editor } from '@tiptap/react';
import { api } from '@/lib/api';

const MAX_BYTES = 10 * 1024 * 1024;

/** Upload one image file and insert it at the current selection. */
export async function uploadAndInsert(editor: Editor, file: File): Promise<void> {
  if (!file.type.startsWith('image/') || file.size > MAX_BYTES) return;
  try {
    const { url } = await api.uploadAsset(file);
    editor.chain().focus().setImage({ src: url, alt: file.name }).run();
  } catch {
    /* swallow — upload errors surface via the network panel; keep typing flow */
  }
}

/** Open a file picker, then upload + insert the chosen image. */
export function pickAndUploadImage(editor: Editor): void {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';
  input.onchange = () => {
    const file = input.files?.[0];
    if (file) void uploadAndInsert(editor, file);
  };
  input.click();
}

/** Pull image files out of a paste/drop event (empty if none). */
export function imageFilesFrom(items: DataTransferItemList | null): File[] {
  if (!items) return [];
  const files: File[] = [];
  for (const item of Array.from(items)) {
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      const file = item.getAsFile();
      if (file) files.push(file);
    }
  }
  return files;
}
