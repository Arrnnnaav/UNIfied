import { Route, Routes } from 'react-router-dom';
import { RedirectIfSignedIn, RequireOperator, RequireStudent } from '@/auth/guards';
import { AppLayout } from '@/layouts/AppLayout';
import { OperatorLayout } from '@/layouts/OperatorLayout';
import { NotFoundPage } from '@/features/NotFoundPage';
import { LoginPage } from '@/features/auth/LoginPage';
import { RegisterPage } from '@/features/auth/RegisterPage';
import { OperatorLoginPage } from '@/features/auth/OperatorLoginPage';
import { OnboardingPage } from '@/features/onboarding/OnboardingPage';
import { TodayPage } from '@/features/today/TodayPage';
import { RoadmapPage } from '@/features/roadmap/RoadmapPage';
import { ResourcesPage } from '@/features/resources/ResourcesPage';
import { TutorPage } from '@/features/tutor/TutorPage';
import { PointAskPage } from '@/features/pointask/PointAskPage';
import { MilestonesPage } from '@/features/milestones/MilestonesPage';
import { MonitoringPage } from '@/features/monitoring/MonitoringPage';
import { ProfilePage } from '@/features/profile/ProfilePage';
import { OverviewPage } from '@/features/operator/OverviewPage';
import { UsersPage } from '@/features/operator/UsersPage';
import { ResourcesPage as OperatorResourcesPage } from '@/features/operator/ResourcesPage';
import { SpatialPage } from '@/features/operator/SpatialPage';
import { PackagesPage } from '@/features/operator/PackagesPage';
import { AnalyticsPage } from '@/features/operator/AnalyticsPage';
import { MonitoringPage as OperatorMonitoringPage } from '@/features/operator/MonitoringPage';

export default function App() {
  return (
    <Routes>
      <Route element={<RedirectIfSignedIn />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      <Route path="/operator/login" element={<OperatorLoginPage />} />
      <Route element={<RequireStudent />}>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<TodayPage />} />
          <Route path="/roadmap" element={<RoadmapPage />} />
          <Route path="/resources" element={<ResourcesPage />} />
          <Route path="/tutor" element={<TutorPage />} />
          <Route path="/point-and-ask" element={<PointAskPage />} />
          <Route path="/milestones" element={<MilestonesPage />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
      </Route>
      <Route element={<RequireOperator />}>
        <Route element={<OperatorLayout />}>
          <Route path="/operator" element={<OverviewPage />} />
          <Route path="/operator/users" element={<UsersPage />} />
          <Route path="/operator/resources" element={<OperatorResourcesPage />} />
          <Route path="/operator/spatial" element={<SpatialPage />} />
          <Route path="/operator/packages" element={<PackagesPage />} />
          <Route path="/operator/analytics" element={<AnalyticsPage />} />
          <Route path="/operator/monitoring" element={<OperatorMonitoringPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
