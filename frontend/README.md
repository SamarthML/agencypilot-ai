# AgencyPilot AI: frontend

Next.js 16 (App Router) · TypeScript · Tailwind v4 · shadcn/ui · Framer Motion · Recharts.

```powershell
Copy-Item .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                               # http://localhost:3000
npm run lint; npx tsc --noEmit; npm run build
```

The backend must be running for the API status dot in the top bar to turn green.
See the root [CLAUDE.md](../CLAUDE.md) for conventions and full run instructions.
