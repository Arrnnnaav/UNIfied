import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { Button } from '@/components';

const TABS = [['/operator', 'Overview'], ['/operator/users', 'Users'], ['/operator/resources', 'Resources'], ['/operator/spatial', 'Spatial review'], ['/operator/packages', 'Packages'], ['/operator/analytics', 'Analytics'], ['/operator/monitoring', 'Monitoring']] as const;

export function OperatorLayout() {
  const { me, signOut } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="h-[60px] px-6 flex items-center gap-4 bg-surface rule">
        <span className="font-display text-xl"><span className="text-accent2">▣</span> StudyOS</span>
        <span className="label border border-accent2 text-accent2 px-2 py-0.5">Operator</span>
        <nav className="ml-6 flex gap-1">{TABS.map(([to, label]) => <NavLink key={to} to={to} end={to === '/operator'} className={({ isActive }) => `px-3 py-1.5 rounded text-[13px] ${isActive ? 'bg-accent2-tint text-accent2' : 'text-dim hover:text-text'}`}>{label}</NavLink>)}</nav>
        <span className="ml-auto text-muted font-mono text-[12px]">{me?.email}</span>
        <Button variant="ghost" size="sm" onClick={signOut}>Sign out</Button>
      </header>
      <main className="p-8 max-w-[1300px]"><Outlet /></main>
    </div>
  );
}
