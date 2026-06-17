import { describe, it, expect, beforeEach } from 'vitest';
import { useUiStore } from './useUiStore';

beforeEach(() => {
  useUiStore.setState({ toasts: [], confirm: null });
});

describe('useUiStore confirm', () => {
  it('ask() resolves true when confirmed', async () => {
    const { ask } = useUiStore.getState();
    const promise = ask('proceed?');
    expect(useUiStore.getState().confirm?.message).toBe('proceed?');
    useUiStore.getState().resolveConfirm(true);
    await expect(promise).resolves.toBe(true);
    expect(useUiStore.getState().confirm).toBeNull();
  });

  it('ask() resolves false when cancelled', async () => {
    const promise = useUiStore.getState().ask('proceed?');
    useUiStore.getState().resolveConfirm(false);
    await expect(promise).resolves.toBe(false);
  });
});

describe('useUiStore toasts', () => {
  it('pushes and dismisses', () => {
    useUiStore.getState().pushToast('done', 'success');
    const { toasts } = useUiStore.getState();
    expect(toasts).toHaveLength(1);
    expect(toasts[0]).toMatchObject({ message: 'done', tone: 'success' });
    useUiStore.getState().dismissToast(toasts[0].id);
    expect(useUiStore.getState().toasts).toHaveLength(0);
  });
});
