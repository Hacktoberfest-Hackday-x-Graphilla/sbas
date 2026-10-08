# RealAI Toolkit 2.0

A polished, event-ready, free-first AI operations workspace. This version is designed to feel like a real product rather than a generic AI chat UI.

## What is new

- 10 focused real-life tools: Writer, Summarizer, Email, Meeting Notes, Resume Coach, Planner, Translator, Code Reviewer, Data Helper, Study Coach.
- Professional command-center dashboard with live system health, usage stats, recent activity and a custom 3D CSS scene.
- Real REST API with JSON endpoints for tools, generation, history, statistics, settings and provider diagnostics.
- SQLite DBMS with persisted generations, favorites, latency metrics, indexed history and settings.
- API Playground inside the product so judges can call the backend and inspect JSON responses.
- Provider adapters for OpenRouter and Gemini, selected server-side. The app never exposes keys in frontend JavaScript.
- Explicit offline fallback for demonstrations without an API key.
- Rate limiting, input-size protection and safer prompt handling.
- History actions: filter, save/favorite, copy, delete.
- Responsive mobile layout.
- Zero external Python packages. The server uses only Python's standard library.

## Run

```bat
python server.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Real AI setup

Copy `.env.example` to `.env` and configure a provider.

```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=openrouter/free
```

or:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
```

Never put a provider secret into `static/app.js` or any frontend file.

## Main API

- `GET /api/health`
- `GET /api/tools`
- `GET /api/stats`
- `GET /api/history?limit=100`
- `GET /api/history/<id>`
- `POST /api/ai`
- `POST /api/provider/test`
- `PUT /api/history/<id>/favorite`
- `DELETE /api/history/<id>`
- `GET /api/settings`
- `PUT /api/settings`

### Example generation request

```json
{
  "tool": "writer",
  "mode": "professional",
  "input": "Rewrite this message for my teacher: I cannot come tomorrow because I am sick."
}
```

## Demo flow for judges

1. Start the server.
2. Open Overview and show the live health panel plus the 3D scene.
3. Open AI Tools and run Writer or Meeting Notes with a real sample.
4. Show the generated result and the saved generation ID/latency.
5. Open History and favorite the result.
6. Open Analytics to show usage and provider statistics.
7. Open API Playground and call `/api/health` then `/api/ai`.

The product is intentionally honest: when no provider is configured, the UI identifies the offline fallback rather than pretending a local rule-based response is a full AI model.
