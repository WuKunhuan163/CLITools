# logic/assistant/ — Assistant GUI & Server

Web-based assistant interface providing the HTML GUI for the LLM agent system.

## Key Subdirectories

| Directory | Purpose |
|-----------|---------|
| `gui/server.py` | HTTP server with SSE, serving the assistant frontend |
| `gui/static/` | HTML, CSS, JS for the frontend |

## API Endpoints (partial list)

### Sessions
- `GET /api/sessions` — List chat sessions
- `POST /api/sessions` — Create session

### Models & Providers
- `GET /api/model/list` — List configured models
- `POST /api/model/switch` — Switch active model
- `GET /api/provider/guide` — Get setup guide for a provider

### Brain (new)
- `GET /api/brain/blueprints` — List available brain blueprints
- `GET /api/brain/instances` — List brain instances
- `GET /api/brain/active` — Get active brain instance and type
- `POST /api/brain/instance` — Create brain instance from blueprint
- `POST /api/brain/switch` — Switch active brain
- `POST /api/brain/audit` — Audit a blueprint

### Settings
- `POST /api/settings/open` — Open settings panel
- `POST /api/settings/close` — Close settings panel
