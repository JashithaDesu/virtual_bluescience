import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import type { Role } from '../lib/types';

export default function RoleRoute({ role }: { role: Role }) {
  const { membership } = useAuth();
  if (membership?.role !== role) {
    return <Navigate to={membership?.role === 'staff' ? '/compare' : '/profile'} replace />;
  }
  return <Outlet />;
}
