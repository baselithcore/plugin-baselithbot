import { authHeaders } from "../auth";
import { BASE } from "./_base";
import type { ActivePolicy, RecentActivity, WorkspaceQueue } from "./types";

export async function getWorkspaceQueue(): Promise<WorkspaceQueue> {
  const res = await fetch(`${BASE}/workspace/queue`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`queue failed: ${res.status}`);
  return res.json();
}

export async function getActivePolicies(): Promise<ActivePolicy[]> {
  const res = await fetch(`${BASE}/workspace/active-policies`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`active-policies failed: ${res.status}`);
  return res.json();
}

export async function getRecentActivity(limit = 5): Promise<RecentActivity[]> {
  const res = await fetch(`${BASE}/workspace/recent-activity?limit=${limit}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`recent-activity failed: ${res.status}`);
  return res.json();
}
