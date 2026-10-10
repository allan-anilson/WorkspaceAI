# WorkspaceAI Frontend

Minimal Next.js scaffold.

Run locally:

```bash
cd frontend
npm install
npm run dev
```

This frontend uses TypeScript.

It calls the backend directly — set `NEXT_PUBLIC_API_BASE` to the full backend API base URL (including the `/api/v1` prefix), for example:

```bash
# in frontend/.env.local
NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
```

The frontend will build WebSocket URLs from the same backend origin so the browser connects directly to the backend (no server-to-server proxying).
