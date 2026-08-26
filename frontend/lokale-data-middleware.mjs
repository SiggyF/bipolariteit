import { readFile } from 'node:fs/promises';
import { extname, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Dev-only static server voor data/export/gepubliceerd/ (issue #112/#218):
// laat `PUBLIC_DATA_BASE_URL=/lokale-data make dev` een nog niet
// gepubliceerde exportwijziging lokaal testen i.p.v. de (mogelijk
// verouderde) jsDelivr-CDN-kopie van bipolariteit-data die alle
// [naam].astro-pagina's normaal als default gebruiken.
//
// Als Vite-dev-middleware i.p.v. een Astro-pagina/-route: een route onder
// src/pages/ met prerender=false vereist een SSR-adapter, ook puur om in
// `astro dev` te draaien -- `astro build` faalt dan zonder adapter
// ([NoAdapterInstalled]), ook al gebruikt de site die route zelf nooit
// (output: 'static', geen adapter, zie astro.config.mjs). Deze
// astro:server:setup-hook vuurt uitsluitend tijdens `astro dev`, dus raakt
// build/deploy op geen enkele manier.
const GEPUBLICEERD_DIR = resolve(fileURLToPath(new URL('.', import.meta.url)), '../data/export/gepubliceerd');

const CONTENT_TYPES = { '.json': 'application/json' };

export function lokaleDataMiddleware() {
  return {
    name: 'lokale-data-middleware',
    hooks: {
      'astro:server:setup': ({ server }) => {
        server.middlewares.use('/lokale-data', async (req, res) => {
          const relPath = normalize(decodeURIComponent(req.url.split('?')[0]));
          const filePath = resolve(GEPUBLICEERD_DIR, '.' + relPath);
          // Voorkomt padtraversal (../../etc/passwd) buiten GEPUBLICEERD_DIR.
          if (!filePath.startsWith(GEPUBLICEERD_DIR)) {
            res.statusCode = 403;
            res.end('Forbidden');
            return;
          }
          try {
            const data = await readFile(filePath);
            res.setHeader('Content-Type', CONTENT_TYPES[extname(filePath)] ?? 'application/octet-stream');
            res.end(data);
          } catch {
            res.statusCode = 404;
            res.end('Not found');
          }
        });
      },
    },
  };
}
