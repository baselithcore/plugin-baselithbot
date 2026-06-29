/**
 * Per-plugin tenancy-override API client (admin).
 *
 * Lists loaded plugins with their manifest-declared tenancy and any runtime
 * override, and sets / clears the override. `shared` = 1 tenant ⇒ N users
 * (deployment-derived); `personal` = 1 user ⇒ 1 tenant.
 */

import { fetchWithAuth, handleResponse } from './client';

const API_BASE = '/api/admin/plugins';

export type TenancyMode = 'shared' | 'personal';

export interface PluginTenancyRow {
  plugin_name: string;
  version: string | null;
  system: boolean;
  declared_tenancy: TenancyMode;
  override: TenancyMode | null;
  effective_tenancy: TenancyMode;
  /** System/infra plugin — tenancy is not overridable (would break the system). */
  locked: boolean;
}

export interface PluginTenancyList {
  plugins: PluginTenancyRow[];
}

export async function getPluginTenancy(): Promise<PluginTenancyList> {
  return handleResponse<PluginTenancyList>(await fetchWithAuth(`${API_BASE}/tenancy`));
}

export async function setPluginTenancy(
  pluginName: string,
  mode: TenancyMode | null
): Promise<PluginTenancyRow> {
  const res = await fetchWithAuth(`${API_BASE}/tenancy/${encodeURIComponent(pluginName)}`, {
    method: 'PUT',
    body: JSON.stringify({ mode }),
  });
  return handleResponse<PluginTenancyRow>(res);
}
