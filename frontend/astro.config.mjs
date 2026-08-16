// @ts-check
import { defineConfig } from 'astro/config';

import vue from '@astrojs/vue';

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
  }
});