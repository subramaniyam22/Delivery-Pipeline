'use client';

import { useEffect, useRef, useState } from 'react';
import { usersAPI } from './api';
import {
  applyDevRoleOverride,
  getCurrentUser,
  getDevRoleOverride,
  getToken,
  logout,
  setCurrentUser,
  setDevRoleOverride,
  type User,
} from './auth';
import { getCapabilities, roleToCapabilities, type Capability, type Role } from './rbac';

type CurrentUserResult = {
  user: User | null;
  role: Role | null;
  capabilities: Capability[];
  isLoading: boolean;
  error: string | null;
};

const decodeJwt = (token: string | null): Record<string, any> | null => {
  if (!token) return null;
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
};

const toRole = (value?: string | null): Role | null => {
  if (!value) return null;
  if (Object.prototype.hasOwnProperty.call(roleToCapabilities, value)) {
    return value as Role;
  }
  return null;
};

export const useCurrentUser = (): CurrentUserResult => {
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const didForceLogout = useRef(false);
  const didLog = useRef(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setIsLoading(false);
      setError('Not authenticated');
      return;
    }

    const cachedUser = getCurrentUser();
    const devRole = getDevRoleOverride();
    const cachedRole = toRole(cachedUser?.role);
    const decoded = decodeJwt(token);
    const decodedRole = toRole(decoded?.role);

    if (cachedUser) {
      setUser(cachedUser);
      if (devRole) {
        setRole(devRole);
      } else if (cachedRole) {
        setRole(cachedRole);
      } else if (decodedRole) {
        setRole(decodedRole);
      }
    } else if (decodedRole) {
      setRole(decodedRole);
    }

    let mounted = true;
    usersAPI.me()
      .then((res) => {
        if (!mounted) return;
        const freshUser = res.data as User;
        setCurrentUser(freshUser);
        if (devRole) {
          setDevRoleOverride(devRole);
        }
        const adjusted = applyDevRoleOverride(freshUser);
        setUser(adjusted);
        const freshRole = toRole(adjusted?.role) || decodedRole;
        if (!freshRole) {
          setError('Role missing; please re-login.');
          if (!didForceLogout.current) {
            didForceLogout.current = true;
            logout();
          }
          return;
        }
        setRole(freshRole);
        setError(null);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err?.response?.data?.detail || 'Failed to load current user');
      })
      .finally(() => {
        if (!mounted) return;
        setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    setCapabilities(getCapabilities(role));
  }, [role]);

  useEffect(() => {
    if (process.env.NODE_ENV !== 'production' && role && !didLog.current) {
      const samples = getCapabilities(role).slice(0, 3);
      console.info('[RBAC] role:', role, 'sample capabilities:', samples);
      didLog.current = true;
    }
  }, [role]);

  return { user, role, capabilities, isLoading, error };
};
