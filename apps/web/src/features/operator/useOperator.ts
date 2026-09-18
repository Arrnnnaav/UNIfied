import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';

export interface OperatorOverview {
  users: number; goals: number; topics: number; resources: number; ingestion_ready: number;
  documents: number; chunks: number; ingestion_jobs: number; spatial_contexts: number;
  learning_sessions: number; completed_sessions: number; packages: number; published_packages: number;
  monitoring_dashboards: number; spatial_avg_confidence: number; spatial_low_confidence: number;
  spatial_avg_latency_ms: number; model_routes: Record<string, { provider?: string; model?: string }>; privacy: string;
}

export interface OperatorUser { id: string; name: string; role: string; created_at: string }
export interface OperatorGoal { id: string; title: string; owner_id: string; status: string; topics: number; resources: number }
export interface OperatorResource { id: string; title: string; source_type: string; status: string; trust_status: string; has_content: boolean; document_count: number }
export interface IngestionJob { id: string; resource_id: string; kind: string; status: string; progress: number; error: string | null }
export interface SpatialReviewItem { id: string; goal_id: string | null; confidence: number; review_status: string; page_title: string; processing_ms: number; utterance_preview: string }
export interface AuditEntry { id: string; actor_id: string; action: string; entity_type: string; entity_id: string; created_at: string }
export interface OperatorPackage { id: string; slug: string; title: string; version: string; status: string; updated_at: string }
export interface OperatorDashboard { id: string; name: string; status: string; access_code: string }

export interface OperatorSnapshot {
  users: OperatorUser[]; goals: OperatorGoal[]; resources: OperatorResource[];
  ingestion_jobs: IngestionJob[]; spatial_review: SpatialReviewItem[]; audit_log: AuditEntry[];
  packages: OperatorPackage[]; monitoring_dashboards: OperatorDashboard[];
  privacy: { raw_resource_text: boolean; raw_screen_pixels: boolean; operator_access: string };
}

export interface ModelRuntime { count: number; p50_latency_ms: number; p95_latency_ms: number; fallback_rate: number; failures: number; providers: string[] }
export interface OperatorAnalytics {
  mastery_buckets: { not_started: number; developing: number; mastered: number };
  resource_trust: Record<string, number>;
  ingestion_status: Record<string, number>;
  spatial_cost: { today_usd: number; by_provider_usd: Record<string, number>; asks_today: number; review: Record<string, number>; client_versions: Record<string, number> };
  spatial: { count: number; low_confidence: number; avg_confidence: number; avg_latency_ms: number; p50_latency_ms: number; p95_latency_ms: number; max_latency_ms: number };
  quality: { ingestion_failure_rate: number; trusted_resources: number; spatial_corrections: number; spatial_correction_rate: number };
  assessment: { attempts: number; average_score: number };
  review: { due: number; scheduled: number };
  sessions: { total: number; planned: number; active: number; completed: number; minutes: number };
  model_health: { embedding_backend: string; local_embedding_enabled: boolean; tutor_route: { provider?: string; model?: string }; spatial_route: { provider?: string; model?: string }; vision_route: { provider?: string; model?: string }; cloud_fallback_configured: boolean; runtime: Record<string, ModelRuntime> };
  privacy: string;
}

export interface CoverageTopic { topic_id: string; title: string; objectives: number; covered_objectives: number; coverage: number }
export interface OperatorCoverage { topics: CoverageTopic[]; content_gaps: number; average_coverage: number; method: string; privacy: string }

export const useOverview = () => useQuery({ queryKey: ['operator', 'overview'], queryFn: () => api<OperatorOverview>('/api/operator/overview') });
export const useSnapshot = () => useQuery({ queryKey: ['operator', 'snapshot'], queryFn: () => api<OperatorSnapshot>('/api/operator/snapshot') });
export const useAnalytics = () => useQuery({ queryKey: ['operator', 'analytics'], queryFn: () => api<OperatorAnalytics>('/api/operator/analytics') });
export const useCoverage = () => useQuery({ queryKey: ['operator', 'coverage'], queryFn: () => api<OperatorCoverage>('/api/operator/coverage') });

export function useOperatorActions() {
  const client = useQueryClient();
  const invalidate = () => client.invalidateQueries({ queryKey: ['operator'] });

  const reviewSpatial = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'confirm' | 'dismiss' }) =>
      api(`/api/operator/spatial/${id}/review`, { method: 'PATCH', json: { action } }),
    onSuccess: invalidate,
  });
  const setTrust = useMutation({
    // backend takes status as a query param: PATCH .../trust?status=verified
    mutationFn: ({ id, status }: { id: string; status: 'verified' | 'rejected' | 'unverified' }) =>
      api(`/api/operator/resources/${id}/trust?status=${encodeURIComponent(status)}`, { method: 'PATCH' }),
    onSuccess: invalidate,
  });
  const retryJob = useMutation({
    mutationFn: (id: string) => api(`/api/operator/ingestion/${id}/retry`, { method: 'POST' }),
    onSuccess: invalidate,
  });
  const createPackage = useMutation({
    mutationFn: (body: { slug: string; title: string; description?: string; version: string; manifest: Record<string, unknown>; status?: string }) =>
      api<OperatorPackage>('/api/operator/packages', { method: 'POST', json: body }),
    onSuccess: invalidate,
  });
  const uploadPackage = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return api<OperatorPackage>('/api/operator/packages/upload', { method: 'POST', body: form });
    },
    onSuccess: invalidate,
  });
  const setPackageStatus = useMutation({
    // backend takes status as a query param: PATCH .../status?status=published
    mutationFn: ({ id, status }: { id: string; status: 'draft' | 'published' | 'archived' }) =>
      api<OperatorPackage>(`/api/operator/packages/${id}/status?status=${encodeURIComponent(status)}`, { method: 'PATCH' }),
    onSuccess: invalidate,
  });
  const createDashboard = useMutation({
    mutationFn: ({ name, leader_student_id }: { name: string; leader_student_id: string }) =>
      api<OperatorDashboard>('/api/operator/monitoring-dashboards', { method: 'POST', json: { name, leader_student_id, description: '' } }),
    onSuccess: invalidate,
  });
  const enroll = useMutation({
    mutationFn: ({ id, student_id }: { id: string; student_id: string }) =>
      api(`/api/operator/monitoring-dashboards/${id}/students`, { method: 'POST', json: { student_id } }),
    onSuccess: invalidate,
  });

  return { reviewSpatial, setTrust, retryJob, createPackage, uploadPackage, setPackageStatus, createDashboard, enroll };
}
