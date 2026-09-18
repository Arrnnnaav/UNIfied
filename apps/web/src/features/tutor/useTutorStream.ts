import { useCallback, useEffect, useRef, useState } from 'react';
import { apiStream, ApiError } from '@/api/client';
import { readSse } from '@/api/sse';

export interface TutorCitation { title: string; snippet: string }
export interface TutorAnswer { answer: string; citations: TutorCitation[]; evidence?: unknown[] }
export interface TutorAskBody { question: string; goal_id?: string; topic_id?: string; spatial_context_id?: string }
export type TutorStatus = 'idle' | 'retrieving' | 'done' | 'error';

export function useTutorStream() {
  const [status, setStatus] = useState<TutorStatus>('idle');
  const [streamed, setStreamed] = useState('');
  const [answer, setAnswer] = useState<TutorAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => { controllerRef.current?.abort(); setStatus(s => (s === 'done' || s === 'error' ? s : 'idle')); }, []);
  useEffect(() => () => { controllerRef.current?.abort(); }, []);

  const ask = useCallback(async (body: TutorAskBody) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setStatus('idle');
    setStreamed('');
    setAnswer(null);
    setError(null);
    try {
      const response = await apiStream('/api/tutor/ask/stream', body, controller.signal);
      if (!response.body) throw new Error('stream unavailable');
      await readSse(response.body, (name, data) => {
        if (controller.signal.aborted) return;
        if (name === 'status') setStatus('retrieving');
        else if (name === 'delta') setStreamed(s => s + (typeof data?.text === 'string' ? data.text : ''));
        else if (name === 'complete') { setAnswer({ answer: data.answer ?? '', citations: data.citations ?? [], evidence: data.evidence }); setStatus('done'); }
        else if (name === 'error') {
          const detail = data?.detail;
          setError(typeof detail === 'string' ? detail : (detail?.message || 'tutor request failed'));
          setStatus('error');
        }
      }, controller.signal);
    } catch (err) {
      if (controller.signal.aborted || (err as { name?: string })?.name === 'AbortError') {
        setStatus(s => (s === 'done' || s === 'error' ? s : 'idle'));
        return;
      }
      setError(err instanceof ApiError ? err.message : (err instanceof Error ? err.message : 'tutor request failed'));
      setStatus('error');
    }
  }, []);

  return { ask, status, streamed, answer, error, cancel };
}
