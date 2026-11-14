import { Navigate, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import Header from './Header';
import Footer from './Footer';

export default function ProtectedLayout() {
  const { loading, session, error, signOut } = useAuth();
  const navigate = useNavigate();

  if (loading) return <div className="flex min-h-screen items-center justify-center text-gray-500">Loading…</div>;
  if (!session) return <Navigate to="/login" replace />;

  if (error) {
    return (
      <div className="mx-auto max-w-xl p-6">
        <div className="rounded-lg border border-gray-300 bg-white p-6">
          <h1 className="mb-2 text-lg font-semibold">Setup problem</h1>
          <p className="mb-4 text-sm text-gray-700">{error}</p>
          <button
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100"
            onClick={async () => { await signOut(); navigate('/login'); }}
          >
            Log out
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <Header />
      <main className="mx-auto w-full max-w-5xl flex-1 p-6">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
