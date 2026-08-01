## Development

Start/stop the background dev server via de Makefile-targets in de repo-root,
niet met rauwe `astro dev`-commando's:

```
make dev       # start (cd frontend && npx astro dev --background --host 0.0.0.0)
make dev-stop  # stop (cd frontend && npx astro dev stop)
```

Voor status/logs van de lopende server volstaat wel het rauwe commando:
`cd frontend && npx astro dev status` / `npx astro dev logs`.

## Documentation

Full documentation: https://docs.astro.build

Consult these guides before working on related tasks:

- [Adding pages, dynamic routes, or middleware](https://docs.astro.build/en/guides/routing/)
- [Working with Astro components](https://docs.astro.build/en/basics/astro-components/)
- [Using React, Vue, Svelte, or other framework components](https://docs.astro.build/en/guides/framework-components/)
- [Adding or managing content](https://docs.astro.build/en/guides/content-collections/)
- [Adding styles or using Tailwind](https://docs.astro.build/en/guides/styling/)
- [Supporting multiple languages](https://docs.astro.build/en/guides/internationalization/)
