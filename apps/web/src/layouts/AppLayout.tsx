import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { Button } from '@/components';

const NAV = [['/', 'Today', '⌂'], ['/roadmap', 'Roadmap', '▦'], ['/resources', 'Resources', '◈'], ['/tutor', 'Tutor', '✦'], ['/point-and-ask', 'Point & Ask', '⌁'], ['/milestones', 'Milestones', '◆'], ['/monitoring', 'Monitoring', '◉'], ['/profile', 'Profile', '◎']] as const;

export function AppLayout() {
  const { me, signOut } = useAuth();
  const initials = (me?.name || '?').split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase();
  return (
    <div className="min-h-screen flex">
      <aside className="w-[250px] shrink-0 bg-surface border-r border-line flex flex-col p-5">
        <div className="font-display text-2xl flex items-center gap-2"><span className="text-accent">◒</span>StudyOS</div>
        <p className="label mt-8 mb-3">Personal learning system</p>
        <nav className="grid gap-1">
          {NAV.map(([to, label, icon]) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `px-3 py-2 rounded text-[14px] ${isActive ? 'bg-accent-tint text-accent-strong' : 'text-dim hover:bg-surface2 hover:text-text'}`}><span className="mr-2 font-mono">{icon}</span>{label}</NavLink>)}
        </nav>
        <div className="mt-auto pt-4 border-t border-line flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-accent text-bg grid place-items-center font-mono text-[12px] font-semibold">{initials}</div>
          <div className="min-w-0"><p className="truncate text-[14px]">{me?.name}</p><p className="text-muted text-[12px] font-mono">{me?.student_id || me?.email}</p></div>
          <Button variant="ghost" size="sm" onClick={signOut} className="ml-auto">Out</Button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 p-8 max-w-[1200px]"><Outlet /></main>
    </div>
  );
}
