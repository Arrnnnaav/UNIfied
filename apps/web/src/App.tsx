import { Route, Routes } from 'react-router-dom';
import { RedirectIfSignedIn, RequireOperator, RequireStudent } from '@/auth/guards';
import { AppLayout } from '@/layouts/AppLayout';
import { OperatorLayout } from '@/layouts/OperatorLayout';
import { NotFoundPage } from '@/features/NotFoundPage';

const Placeholder = ({ name }: { name: string }) => <h1 className="text-3xl">{name}</h1>;

export default function App() {
  return (
    <Routes>
      <Route element={<RedirectIfSignedIn />}>
        <Route path="/login" element={<Placeholder name="Login" />} />
        <Route path="/register" element={<Placeholder name="Register" />} />
      </Route>
      <Route path="/operator/login" element={<Placeholder name="Operator login" />} />
      <Route element={<RequireStudent />}>
        <Route path="/onboarding" element={<Placeholder name="Onboarding" />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<Placeholder name="Today" />} />
          <Route path="/roadmap" element={<Placeholder name="Roadmap" />} />
          <Route path="/resources" element={<Placeholder name="Resources" />} />
          <Route path="/tutor" element={<Placeholder name="Tutor" />} />
          <Route path="/point-and-ask" element={<Placeholder name="Point & Ask" />} />
          <Route path="/milestones" element={<Placeholder name="Milestones" />} />
          <Route path="/monitoring" element={<Placeholder name="Monitoring" />} />
          <Route path="/profile" element={<Placeholder name="Profile" />} />
        </Route>
      </Route>
      <Route element={<RequireOperator />}>
        <Route element={<OperatorLayout />}>
          <Route path="/operator" element={<Placeholder name="Overview" />} />
          <Route path="/operator/users" element={<Placeholder name="Users" />} />
          <Route path="/operator/resources" element={<Placeholder name="Resources" />} />
          <Route path="/operator/spatial" element={<Placeholder name="Spatial review" />} />
          <Route path="/operator/packages" element={<Placeholder name="Packages" />} />
          <Route path="/operator/analytics" element={<Placeholder name="Analytics" />} />
          <Route path="/operator/monitoring" element={<Placeholder name="Monitoring" />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
