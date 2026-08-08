# SchemaSense — frontend

React (JavaScript) + Vite. A live console for the NL-to-SQL Generator backend:
ask a question, watch it become SQL, see it actually run — including the
self-correction loop and demo-mode "bring your own database" flow.

## Running locally

```bash
cp .env.example .env   # point VITE_API_BASE_URL at your backend if not localhost:8000
npm install
npm run dev
```

The backend must be running (see `../backend/README.md`) and reachable at
`VITE_API_BASE_URL` — its CORS is already wide open for local development.

## Structure

```
src/
  api/client.js        # typed wrapper over the backend's HTTP contract
  hooks/useTheme.js     # light/dark, system-aware, persisted
  lib/parseSchema.js    # parses the backend's schema-context text
  components/
    QueryConsole.jsx    # the input + sample questions — the hero interaction
    ResultPanel.jsx      # routes between success / rejected / exhausted / error
    SqlBlock.jsx          # lightweight SQL keyword highlighting, no dependency
    ResultTable.jsx        # renders returned rows
    SchemaPanel.jsx         # visualizes GET /schema for whichever DB is active
    DemoConnect.jsx          # POST /demo/connect, DELETE /demo/connect/{id}
    HowItWorks.jsx            # the pipeline, mirrored from the backend's docs
  App.jsx               # orchestrates state; no router or state library needed
                         # at this scope — plain useState/useEffect throughout
```

## Design

- Two-hue system: amber for the "human/language" side of the pipeline
  (the question, the drafted SQL), teal for the "machine/data" side (schema,
  execution, results) — the color itself encodes which half of the mechanism
  you're looking at.
- Type: Newsreader (an editorial serif, used italic for anything "spoken" —
  the headline, the question echo) paired with IBM Plex Sans for UI chrome
  and IBM Plex Mono for anything literal — SQL, schema, JSON-shaped data.
- Every component ships both a light and a dark palette (`styles/tokens.css`),
  switchable via the header toggle or inherited from system preference.
