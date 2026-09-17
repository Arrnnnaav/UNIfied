/** Read `event: name\ndata: json\n\n` blocks from a fetch body. Resolves when the stream ends or the signal aborts. */
export async function readSse(body: ReadableStream<Uint8Array>, onEvent: (name: string, data: any) => void, signal?: AbortSignal): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const onAbort = () => reader.cancel().catch(() => {});
  signal?.addEventListener('abort', onAbort);
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';
      for (const block of blocks) {
        const match = block.match(/^event: (.+)\ndata: (.+)$/s);
        if (!match) continue;
        let data: unknown = match[2];
        try { data = JSON.parse(match[2]); } catch { /* keep raw */ }
        onEvent(match[1].trim(), data);
      }
    }
  } finally {
    signal?.removeEventListener('abort', onAbort);
  }
}
