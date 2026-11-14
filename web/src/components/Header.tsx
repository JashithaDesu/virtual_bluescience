import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { USE_MOCK } from '../lib/supabase';
import Logo from './Logo';

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium ${
    isActive ? 'bg-white/15 text-white' : 'text-white/70 hover:bg-white/10 hover:text-white'
  }`;

export default function Header() {
  const { session, membership, company, signOut } = useAuth();
  const navigate = useNavigate();
  const isStaff = membership?.role === 'staff';
  const who = isStaff ? 'Blue Science Park staff' : company?.name ?? '';
  const initial = (session?.email ?? '?').charAt(0).toUpperCase();

  return (
    <>
      {USE_MOCK && (
        <div className="bg-amber-100 px-4 py-1 text-center text-xs font-medium text-amber-900">
          MOCK DATA: not connected to the database
        </div>
      )}
      <header className="bg-brand-900 text-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-8 gap-y-3 px-6 py-3">
          <div className="flex items-center gap-3">
            <Logo />
            <div className="leading-tight">
              <p className="text-sm font-semibold">Virtual Science Park</p>
              {who && <p className="text-xs text-white/60">{who}</p>}
            </div>
          </div>
          <nav className="flex gap-1">
            {isStaff ? (
              <NavLink to="/compare" className={linkClass}>Compare</NavLink>
            ) : (
              <>
                <NavLink to="/profile" className={linkClass}>Profile</NavLink>
                <NavLink to="/feed" className={linkClass}>Opportunities</NavLink>
                <NavLink to="/ask" className={linkClass}>Ask</NavLink>
              </>
            )}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden text-xs text-white/60 sm:inline">{session?.email}</span>
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500 text-sm font-semibold">
              {initial}
            </span>
            <button
              className="rounded-md border border-white/25 px-3 py-1 text-sm text-white/90 hover:bg-white/10"
              onClick={async () => { await signOut(); navigate('/login'); }}
            >
              Log out
            </button>
          </div>
        </div>
      </header>
    </>
  );
}