import { getToken } from './client';

export function openScanStream(scanId: string): WebSocket {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return new WebSocket(
    `${proto}://${location.host}/red-agent/ws/scans/${scanId}?token=${encodeURIComponent(getToken())}`
  );
}

export function openActivityStream(
  opts: { eventPrefix?: string[]; engagementId?: string } = {}
): WebSocket {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const usp = new URLSearchParams();
  usp.set('token', getToken());
  for (const p of opts.eventPrefix ?? []) {
    if (p) usp.append('event_prefix', p);
  }
  if (opts.engagementId) usp.set('engagement_id', opts.engagementId);
  return new WebSocket(`${proto}://${location.host}/red-agent/ws/activity?${usp.toString()}`);
}
