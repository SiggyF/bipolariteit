// @ts-check
import { defineConfig } from 'astro/config';

import vue from '@astrojs/vue';
import sirv from 'sirv';
import path from 'node:path';

// https://astro.build/config
export default defineConfig({
  integrations: [vue()],
  // URL-consistentie (docs/taalconventie.md): routes hernoemd naar consistent
  // Nederlands + meervoud. Statische redirects (meta-refresh + canonical, geen
  // serverside 301 -- www.bipolariteit.org draait op Cloudflare Workers static
  // assets zonder eigen Worker-script, zie deploy/wrangler.www.template.jsonc)
  // zodat oude, al-live links blijven werken.
  redirects: {
    '/topics': '/onderwerpen',
    '/topics/[slug]': '/onderwerpen/[slug]',
    '/about': '/over',
    '/partij': '/partijen',
    '/partij/[naam]': '/partijen/[naam]',
    '/persoon': '/personen',
    '/persoon/[naam]': '/personen/[naam]',
    '/perspectief': '/perspectieven',
    '/perspectief/[naam]': '/perspectieven/[naam]',
    '/debat/[id]': '/debatten/[id]',
  },
  vite: {
    plugins: [
      {
        // Dev-only static server voor data/export/gepubliceerd/ (issue
        // #112/#218), op hetzelfde /data-pad als de al bestaande
        // plenair-map-data in public/data/ (die staat er ook in, als kopie --
        // zie lib/dataBaseUrl.ts voor de ene plek waar dit pad vastligt).
        // sirv (al een dependency via Astro/Vite zelf) i.p.v. zelf een
        // bestandsserver bouwen. configureServer vuurt uitsluitend tijdens
        // `astro dev`, raakt build/deploy dus op geen enkele manier.
        name: 'local-data-middleware',
        configureServer(server) {
          const publishedDataDir = path.resolve('../data/export/gepubliceerd');
          server.middlewares.use('/data', sirv(publishedDataDir, { dev: true }));
        },
      },
    ],
  },
});
