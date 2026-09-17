import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import { Spinner } from '@/components';
import { Button } from '@/components';

function Loading() { return <div className="grid place-items-center min-h-screen"><Spinner /></div>; }

/** Any signed-in account. Students without a goal are sent to onboarding (except when already there). */
export function RequireStudent() {
  const { me, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Loading />;
  if (!me) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  if (!me.has_goals && location.pathname !== '/onboarding') return <Navigate to="/onboarding" replace />;
  return <Outlet />;
}

export function RequireOperator() {
  const { me, loading, signOut } = useAuth();
  if (loading) return <Loading />;
  if (!me) return <Navigate to="/operator/login" replace />;
  if (me.role !== 'operator') {
    return (
      <div className="grid place-items-center min-h-screen p-6">
        <div className="bg-surface border border-line p-6 max-w-md">
          <p className="label">Operator</p>
          <h1 className="text-2xl mt-1">This account is not an operator</h1>
          <p className="text-dim mt-2">Signed in as {me.email} ({me.role}). Operator access is granted by an existing operator.</p>
          <div className="mt-4 flex gap-2"><Button onClick={signOut} variant="ghost">Sign out</Button><Button onClick={() => window.location.assign('/')}>Go to StudyOS</Button></div>
        </div>
      </div>
    );
  }
  return <Outlet />;
}

/** Login/register pages bounce signed-in users to the app. */
export function RedirectIfSignedIn() {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  if (me) return <Navigate to={me.role === 'operator' ? '/operator' : '/'} replace />;
  return <Outlet />;
}
