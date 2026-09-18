import { describe, it, expect } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useTutorStream } from './useTutorStream';

function streamResponse(events: string[], opts?: { hold?: boolean }) {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      for (const event of events) controller.enqueue(encoder.encode(event));
      if (!opts?.hold) controller.close();
    },
  });
  return new Response(stream, { status: 200, headers: { 'content-type': 'text/event-stream' } });
}

describe('useTutorStream', () => {
  it('streams status then complete and exposes the answer', async () => {
    globalThis.fetch = (async () => streamResponse([
      'event: status\ndata: {"status":"retrieving"}\n\n',
      'event: complete\ndata: {"answer":"42","citations":[]}\n\n',
    ])) as unknown as typeof fetch;

    const { result } = renderHook(() => useTutorStream());
    await act(async () => { await result.current.ask({ question: 'meaning of life?' }); });

    await waitFor(() => expect(result.current.status).toBe('done'));
    expect(result.current.answer?.answer).toBe('42');
    expect(result.current.answer?.citations).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it('accumulates delta text while retrieving', async () => {
    globalThis.fetch = (async () => streamResponse([
      'event: status\ndata: {"status":"retrieving"}\n\n',
      'event: delta\ndata: {"text":"fo"}\n\n',
      'event: delta\ndata: {"text":"o"}\n\n',
      'event: complete\ndata: {"answer":"foo","citations":[]}\n\n',
    ])) as unknown as typeof fetch;

    const { result } = renderHook(() => useTutorStream());
    await act(async () => { await result.current.ask({ question: 'q' }); });
    await waitFor(() => expect(result.current.status).toBe('done'));
    expect(result.current.streamed).toBe('foo');
  });

  it('cancel() aborts an in-flight request', async () => {
    let observedSignal: AbortSignal | undefined;
    globalThis.fetch = (async (_input: unknown, init?: RequestInit) => {
      observedSignal = init?.signal ?? undefined;
      return streamResponse(['event: status\ndata: {"status":"retrieving"}\n\n'], { hold: true });
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useTutorStream());
    let pending: Promise<void>;
    await act(async () => { pending = result.current.ask({ question: 'q' }); await Promise.resolve(); });
    await waitFor(() => expect(result.current.status).toBe('retrieving'));
    act(() => { result.current.cancel(); });
    expect(observedSignal?.aborted).toBe(true);
    await act(async () => { await pending!; });
    expect(result.current.status).toBe('idle');
  });

  it('surfaces error events', async () => {
    globalThis.fetch = (async () => streamResponse([
      'event: error\ndata: {"detail":{"message":"boom"}}\n\n',
    ])) as unknown as typeof fetch;

    const { result } = renderHook(() => useTutorStream());
    await act(async () => { await result.current.ask({ question: 'q' }); });
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.error).toBe('boom');
  });
});
