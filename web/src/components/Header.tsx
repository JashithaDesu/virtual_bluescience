import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { USE_MOCK } from '../lib/supabase';

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm ${isActive ? 'font-semibold underline underline-offset-4' : 'text-gray-600 hover:text-gray-900'}`;

export default function Header() {
  const { session, membership, company, signOut } = useAuth();
  const navigate = useNavigate();
  const isStaff = membership?.role === 'staff';

  return (
    <>
      {USE_MOCK && (
        <div className="bg-amber-100 px-4 py-1 text-center text-xs font-medium text-amber-900">
          MOCK DATA — not connected to the database
        </div>
      )}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-6 px-6 py-3">
          <div className="flex items-baseline gap-3">
            <span className="font-bold">Virtual Science Park</span>
            <span className="text-sm text-gray-600">{isStaff ? 'Blue Science Park staff' : company?.name ?? ''}</span>
          </div>
          <nav className="flex gap-4">
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
            <span className="text-xs text-gray-500">{session?.email}</span>
            <button
              className="rounded-md border border-gray-300 px-3 py-1 text-sm hover:bg-gray-100"
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
