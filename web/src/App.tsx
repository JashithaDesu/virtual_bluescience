import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './lib/auth';
import ProtectedLayout from './components/ProtectedLayout';
import RoleRoute from './components/RoleRoute';
import Login from './pages/Login';
import Profile from './pages/Profile';
import Feed from './pages/Feed';
import Ask from './pages/Ask';
import Compare from './pages/Compare';

function Home() {
  const { membership } = useAuth();
  return <Navigate to={membership?.role === 'staff' ? '/compare' : '/profile'} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Home />} />
        <Route element={<RoleRoute role="member" />}>
          <Route path="/profile" element={<Profile />} />
          <Route path="/feed" element={<Feed />} />
          <Route path="/ask" element={<Ask />} />
        </Route>
        <Route element={<RoleRoute role="staff" />}>
          <Route path="/compare" element={<Compare />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
