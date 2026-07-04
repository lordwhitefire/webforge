# Meta Engineering — Corrections Log

Rules learned from developer corrections.

---

- **[2026-07-04T02:15:29.903242+00:00]** Wrong: using localStorage for auth tokens → Right: use httpOnly cookies instead → Rule: Never using localStorage for auth tokens. Use httpOnly cookies instead.
- **[2026-07-04T02:15:29.959894+00:00]** Wrong: putting 'use client' at the top of every file → Right: only mark 'use client' when the component uses hooks or event handlers → Rule: Never putting 'use client' at the top of every file. Only mark 'use client' when the component uses hooks or event handlers.
- **[2026-07-04T02:15:30.018378+00:00]** Wrong: using any for TypeScript types → Right: always use proper types or unknown → Rule: Never using any for TypeScript types. Always use proper types or unknown.
- **[2026-07-04T02:17:44.922106+00:00]** Wrong: using console.log for debugging in production → Right: use proper logging with Sentry → Rule: Never using console.log for debugging in production. Use proper logging with Sentry.
