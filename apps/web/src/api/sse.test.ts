import { readSse } from './sse';

function stream(chunks: string[]) {
  const enc = new TextEncoder();
  return new ReadableStream<Uint8Array>({ start(c) { chunks.forEach(ch => c.enqueue(enc.encode(ch))); c.close(); } });
}

test('parses events split across chunks', async () => {
  const events: [string, unknown][] = [];
  await readSse(stream(['event: status\ndata: {"status":"x"}\n\nevent: del', 'ta\ndata: {"text":"hi"}\n\n']), (n, d) => events.push([n, d]));
  expect(events).toEqual([['status', { status: 'x' }], ['delta', { text: 'hi' }]]);
});
