// Runs apps/extension/geometry.js against a case and prints the JS-side resolution as JSON.
// Usage: node run_js.mjs cases/basic_overlap.json
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const G = createRequire(import.meta.url)(path.join(here, '..', '..', 'apps', 'extension', 'geometry.js'));
const file = process.argv[2];
const kase = JSON.parse(readFileSync(file, 'utf8'));

const out = { marks: [] };
for (const raw of kase.marks) {
  // Polygons without a bbox are raw strokes: derive it like content.js does; otherwise trust the client bbox.
  const mark = raw.type === 'polygon' && raw.x === undefined ? G.strokeToMark(raw.points, raw.role) : { ...raw, width: raw.width || 0, height: raw.height || 0 };
  const ranked = G.rankAnchors(kase.anchors, mark).map(a => a.id);
  out.marks.push({ role: mark.role, bbox: { x: mark.x, y: mark.y, width: mark.width, height: mark.height }, top: ranked[0] || null, ranked });
}
process.stdout.write(JSON.stringify(out));
