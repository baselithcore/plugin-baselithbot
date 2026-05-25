"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "./button";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  busy?: boolean;
  onConfirm: () => void;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive,
  busy,
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-bg-canvas/60 backdrop-blur-[2px] animate-fade-in" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-[min(440px,92vw)] surface-elev rounded-xl border border-border p-5 shadow-popover animate-dialog-in"
          style={{ transform: "translate(-50%, -50%)" }}
        >
          <div className="flex items-start gap-3">
            {destructive && (
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-status-danger/30 bg-status-danger/10 text-status-danger">
                <AlertTriangle size={16} />
              </span>
            )}
            <div className="min-w-0">
              <Dialog.Title className="text-sm font-semibold">
                {title}
              </Dialog.Title>
              {description && (
                <Dialog.Description className="mt-1.5 text-xs leading-5 text-text-muted">
                  {description}
                </Dialog.Description>
              )}
            </div>
          </div>
          <div className="mt-5 flex justify-end gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={busy}
            >
              {cancelLabel}
            </Button>
            <Button
              size="sm"
              variant={destructive ? "danger" : "primary"}
              onClick={onConfirm}
              disabled={busy}
            >
              {busy && <Loader2 size={13} className="animate-spin" />}
              {confirmLabel}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
