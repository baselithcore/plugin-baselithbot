/**
 * Users Hook
 *
 * Manages user data fetching and CRUD operations.
 */

import { useState, useEffect, useCallback } from 'react';
import type {
  User,
  CreateUserRequest,
  UpdateUserRequest,
  CreateUserResponse,
  ResetPasswordResponse,
} from '../types';
import * as api from '../api/users';

interface UseUsersOptions {
  page?: number;
  limit?: number;
  includeInactive?: boolean;
  search?: string;
}

interface UseUsersReturn {
  users: User[];
  total: number;
  page: number;
  limit: number;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  createUser: (data: CreateUserRequest) => Promise<CreateUserResponse>;
  updateUser: (userId: string, data: UpdateUserRequest) => Promise<User>;
  deleteUser: (userId: string) => Promise<void>;
  resetPassword: (userId: string) => Promise<ResetPasswordResponse>;
  unlockUser: (userId: string) => Promise<void>;
  revokeSessions: (userId: string) => Promise<void>;
  disableMFA: (userId: string) => Promise<void>;
  setPage: (page: number) => void;
  setSearch: (search: string) => void;
  setIncludeInactive: (include: boolean) => void;
}

export function useUsers(options: UseUsersOptions = {}): UseUsersReturn {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(options.page || 1);
  const [limit] = useState(options.limit || 20);
  const [includeInactive, setIncludeInactive] = useState(options.includeInactive || false);
  const [search, setSearch] = useState(options.search || '');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.listUsers(page, limit, includeInactive, search || undefined);
      setUsers(response.users);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setIsLoading(false);
    }
  }, [page, limit, includeInactive, search]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const createUser = useCallback(
    async (data: CreateUserRequest): Promise<CreateUserResponse> => {
      const result = await api.createUser(data);
      await refresh();
      return result;
    },
    [refresh]
  );

  const updateUser = useCallback(
    async (userId: string, data: UpdateUserRequest): Promise<User> => {
      const result = await api.updateUser(userId, data);
      await refresh();
      return result;
    },
    [refresh]
  );

  const deleteUser = useCallback(
    async (userId: string): Promise<void> => {
      await api.deleteUser(userId);
      await refresh();
    },
    [refresh]
  );

  const resetPassword = useCallback(async (userId: string): Promise<ResetPasswordResponse> => {
    const result = await api.resetPassword(userId);
    return result;
  }, []);

  const unlockUser = useCallback(
    async (userId: string): Promise<void> => {
      await api.unlockUser(userId);
      await refresh();
    },
    [refresh]
  );

  const revokeSessions = useCallback(
    async (userId: string): Promise<void> => {
      await api.revokeSessions(userId);
      await refresh();
    },
    [refresh]
  );

  const disableMFA = useCallback(
    async (userId: string): Promise<void> => {
      await api.disableMFA(userId);
      await refresh();
    },
    [refresh]
  );

  return {
    users,
    total,
    page,
    limit,
    isLoading,
    error,
    refresh,
    createUser,
    updateUser,
    deleteUser,
    resetPassword,
    unlockUser,
    revokeSessions,
    disableMFA,
    setPage,
    setSearch,
    setIncludeInactive,
  };
}
