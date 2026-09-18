import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';

/** Keys verified against monitoring_summary in services/api/app/main.py. */
export interface MonitoringStudent {
  student_id: string | null;
  name: string;
  college: string;
  year: string;
  branch: string;
  goals: number;
  topics: number;
  average_progress: number;
  average_mastery: number;
  completed_sessions: number;
  session_minutes: number;
  active_days_30: number;
  sessions_last_14_days: number;
  last_activity: string | null;
  on_track: boolean;
}

/** Keys verified against serialize_monitoring_dashboard. */
export interface MonitoringDashboard {
  id: string;
  name: string;
  description: string;
  status: string;
  access_code: string;
  leader: { student_id: string | null; name: string } | null;
  students: MonitoringStudent[];
  student_count: number;
  created_at: string;
}

export const useMonitoringDashboards = () =>
  useQuery({ queryKey: ['monitoring-dashboards'], queryFn: () => api<MonitoringDashboard[]>('/api/monitoring-dashboards') });

export const useMonitoringDashboard = (id: string | null) =>
  useQuery({ queryKey: ['monitoring-dashboards', id], queryFn: () => api<MonitoringDashboard>(`/api/monitoring-dashboards/${id}`), enabled: Boolean(id) });

export function useMonitoringActions() {
  const client = useQueryClient();
  const join = useMutation({
    mutationFn: (accessCode: string) =>
      api<{ dashboard_id: string; status: string }>(`/api/monitoring/join/${encodeURIComponent(accessCode)}`, { method: 'POST' }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['monitoring-dashboards'] }),
  });
  return { join };
}
