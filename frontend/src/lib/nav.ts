import { getCapabilities, type Capability, type Role } from './rbac';
import type { User } from './auth';

export type NavGroup = 'Work' | 'Delivery' | 'Insights' | 'Admin';

export type NavItem = {
  label: string;
  href: string;
  requiredCapabilities: Capability[];
  group: NavGroup;
};

export const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', requiredCapabilities: ['view_dashboard'], group: 'Work' },
  { label: 'Projects', href: '/projects', requiredCapabilities: ['view_projects'], group: 'Work' },
  { label: 'Clients', href: '/client-management', requiredCapabilities: ['view_clients'], group: 'Work' },
  { label: 'Forecast', href: '/forecast', requiredCapabilities: ['view_forecast'], group: 'Delivery' },
  { label: 'Capacity', href: '/capacity', requiredCapabilities: ['view_capacity'], group: 'Delivery' },
  { label: 'Operations', href: '/admin/operations', requiredCapabilities: ['view_operations'], group: 'Delivery' },
  { label: 'Quality', href: '/admin/quality', requiredCapabilities: ['view_quality'], group: 'Delivery' },
  { label: 'Sentiments', href: '/sentiments', requiredCapabilities: ['view_sentiments'], group: 'Insights' },
  { label: 'Reports', href: '/reports', requiredCapabilities: ['view_reports'], group: 'Insights' },
  { label: 'Manage Users', href: '/users', requiredCapabilities: ['manage_users'], group: 'Admin' },
  { label: 'Config', href: '/configuration', requiredCapabilities: ['configure_system'], group: 'Admin' },
  { label: 'Audit Logs', href: '/admin/audit-logs', requiredCapabilities: ['view_audit_logs'], group: 'Admin' },
];

export const getNavForUser = (user?: User | null): NavItem[] => {
  const caps = getCapabilities(user?.role);
  return navItems.filter((item) =>
    item.requiredCapabilities.every((cap) => caps.includes(cap))
  );
};

export const getLandingRouteForRole = (_role?: Role | string | null): string => {
  // All users land on dashboard by default
  return '/dashboard';
};
