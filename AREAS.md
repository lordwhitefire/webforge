# WebForge — The 88 Areas

Every project must consider every area. Mark each one as:
- **[D]** Decided — decision made, documented
- **[S]** Skip — not needed for this project
- **[P]** Pending — needs decision before build starts

---

## SECTION A — APPLIES TO ALL (Websites + Web Apps + Apps)

### 01. Project Setup
- Project name?
- Who is the client?
- Deadline?
- Budget?
- Target audience? (Nigeria, international, both)
- Currency? (Naira, USD, both)
- Domain available?
- Hosting target? (Vercel, Render, VPS, other)
- Environment separation? (dev, staging, production)

### 02. Stack Decisions
- Frontend framework (Next.js, Remix, Astro, React + Vite)
- CSS approach (Tailwind, CSS Modules, styled-components)
- TypeScript or JavaScript?
- Component library? (shadcn/ui, Radix, none)
- Animation library? (Framer Motion, GSAP, CSS only)
- State management? (Zustand, React Query, Context, none)
- Form library? (React Hook Form, native, other)
- Validation? (Zod, Yup, none)

### 03. Design System
- Color tokens (primary, secondary, accent, neutral, error, success)
- Typography (font family, scale, weights)
- Spacing scale
- Border radius convention
- Shadow convention
- Dark mode required?
- Design reference sites or Figma file?
- Which design principles are we following?

### 04. Brand & Identity
- Logo available? (Yes / No / Need to generate)
- Brand colors defined?
- Brand fonts defined?
- Brand voice? (Professional, casual, bold, warm)
- Any brand guidelines document?

### 05. Frontend Architecture
- Folder structure convention
- Component naming convention
- File naming convention
- Server components vs client components strategy (Next.js)
- Where does data fetching happen? (server, client, both)
- Code splitting strategy
- Bundle size budget

### 06. Routing & Navigation
- What are all the pages/routes?
- Mega menu? (How many levels? Static or dynamic?)
- Mobile navigation pattern (drawer, bottom nav, accordion)
- Protected routes? (Which ones require auth?)
- 404 and error pages needed?
- Redirect rules?

### 07. SEO & Discoverability
- robots.txt
- sitemap.xml
- schema.org structured data
- llms.txt
- Meta tags strategy (title, description, OG, Twitter cards)
- Canonical URLs
- Is SEO a priority or secondary concern?

### 08. Performance
- Core Web Vitals targets (LCP, CLS, FID/INP)
- Image optimization strategy (next/image, Cloudinary, manual)
- Lazy loading strategy
- Font loading strategy
- Third party script loading (defer, async, none)
- Caching strategy (browser, CDN, server)
- Target Lighthouse score?

### 09. Responsive & Cross-Device
- Which breakpoints? (mobile, tablet, desktop, wide)
- Mobile-first or desktop-first?
- Which devices must be tested on?
- Touch interactions needed?

### 10. Cross-Browser Compatibility
- Which browsers to support? (Chrome, Firefox, Safari, Edge)
- Safari iOS known issues?
- Minimum browser versions?
- Progressive enhancement or graceful degradation?
- Testing strategy (manual, BrowserStack, other)

### 11. Accessibility (a11y)
- ARIA labels required?
- Keyboard navigation required?
- Color contrast standard (WCAG AA or AAA)?
- Screen reader testing?
- Focus management?
- Is this legally required for the client?

### 12. Assets & Media
- Where are images stored? (Supabase Storage, Cloudinary, S3)
- Who provides product/content images? (Client or we generate)
- Image naming convention
- Video hosting? (YouTube embed, Cloudinary, self-hosted)
- Icon library? (Lucide, HeroIcons, custom SVG)
- Maximum file size limits?

### 13. Error Handling
- Error boundary components (where and how many)
- API error shape (what does an error response look like)
- User-facing error messages (tone, placement)
- Logging tool? (Sentry, console only, custom)
- What happens when Supabase is down?
- What happens when a third party API fails?

### 14. Environment & Configuration
- .env.example maintained and up to date?
- Which variables go in dev vs staging vs production?
- Who has access to production secrets?
- What happens when a key leaks? (rotation plan)
- Feature flags? (How to turn features on/off without deploying)

### 15. Version Control Conventions
- Branch naming convention (feature/, fix/, chore/)
- Commit message format (conventional commits)
- PR process (reviews required?)
- When to tag releases?
- Main branch protection rules?

### 16. Development Workflow
- Linting (ESLint config)
- Formatting (Prettier config)
- Pre-commit hooks (Husky + lint-staged)
- TypeScript strict mode?
- Code review process?

### 17. Testing
- What gets tested? (critical paths only, or everything)
- Unit tests? (Vitest, Jest)
- E2E tests? (Playwright, Cypress)
- Component tests? (Storybook, React Testing Library)
- Who runs tests? (manual, CI)

### 18. Deployment & DevOps
- CI/CD pipeline? (GitHub Actions, Vercel auto-deploy)
- Preview deployments per PR?
- Environment separation (dev/staging/prod)
- How to rollback a bad deployment?
- Build time targets?

### 19. Monitoring & Observability
- Uptime monitoring? (Better Uptime, UptimeRobot)
- Error tracking (Sentry)
- Performance monitoring (Vercel Analytics, Datadog)
- User analytics (Posthog, GA4)
- What alerts exist and who gets notified?

### 20. Legal & Compliance
- Privacy policy page needed?
- Cookie consent banner needed?
- GDPR compliance required? (EU audience)
- Terms of service needed?
- Age restrictions on content?
- NDPR (Nigeria Data Protection Regulation) compliance?
- Does it process personal data of Nigerian citizens?
- Explicit consent requirements for data collection?
- Breach notification timeline (72 hours under NDPR)?
- Data localization requirements?
- Who is the Data Protection Officer (DPO)?

### 21. Documentation
- README
- Changelog
- Inline code comments standard
- API documentation (if applicable)
- Onboarding doc for next developer

### 22. Naming Conventions
- Component names (PascalCase)
- File names (kebab-case or PascalCase)
- CSS class names
- Supabase table names (snake_case)
- Supabase function names
- Variable and function names (camelCase)
- Constants (UPPER_SNAKE_CASE)

### 23. Animation & Interactions
- Do we use Framer Motion?
- Performance budget for animations?
- Page transitions?
- Micro-interactions (hover, click, focus)?
- Loading state animations?
- Reduced motion support?

### 24. Notifications & Feedback
- Toast messages (which library, position, duration)
- Modal/dialog pattern
- Confirmation dialogs (before delete, etc.)
- Loading indicators (skeleton, spinner, both)
- Empty state designs
- Success states

### 25. Forms & Validation
- Form library (React Hook Form)
- Validation library (Zod)
- How are errors displayed to user?
- File upload handling?
- Multi-step forms needed?
- Auto-save on forms?

### 26. Internationalization (i18n)
- Multiple languages needed now or in future?
- Right-to-left support?
- Date and time format per locale?
- Currency format per locale?
- If not now — is the architecture flexible enough to add later?

### 27. Offline & PWA
- Does it need to work offline?
- Install to homescreen?
- Service workers?
- Background sync?
- Important for Nigerian context — power outages and poor connectivity

### 28. Cookie & Session Management
- How long do sessions last?
- Remember me functionality?
- Secure and httpOnly cookies?
- What happens when session expires mid-task?
- Multiple device handling?

### 29. Redirect & URL Management
- 301 vs 302 redirects
- Trailing slash consistency
- URL structure convention (kebab-case)
- Old URLs after restructuring
- Canonical URLs

### 30. Code Splitting & Bundle Size
- Which routes are lazy loaded?
- Bundle analyzer setup (next bundle analyzer)
- Third party library weight audit
- Tree shaking configured?

### 31. Backup & Recovery
- Database backup schedule
- How to rollback a bad migration?
- Disaster recovery plan
- Who is responsible for backups?

### 32. Client Communication
- What questions do we ask client before starting?
- How do we communicate progress? (WhatsApp, email)
- What format are client updates in?
- Who approves designs before build starts?
- What is the handoff process at the end?

### 33. Handoff & Maintenance
- Who maintains after launch? (You, client, third party)
- Admin credentials handoff process
- Client training needed?
- Documentation for next developer
- Support period after launch?

---

## SECTION B — E-COMMERCE SPECIFIC

### 34. Payment Integration
- Payment providers (Paystack for Nigeria, Stripe for international)
- Test mode vs live mode plan
- Webhook handling (what events to listen to)
- Refund flow
- Failed payment handling
- Receipt/invoice generation

### 35. Product Catalog
- How many products at launch?
- Product categories and subcategories
- Product variants (size, color, flavor)
- Product images (how many per product, formats)
- Product descriptions (who writes them)
- Featured products logic
- Related products logic

### 36. Inventory Management
- Auto-tracking or manual?
- Out of stock behavior (hide, show label, allow backorder)
- Low stock alerts?
- Who updates inventory?
- Selling on multiple platforms? (affects inventory count)

### 37. Cart & Checkout
- Cart (multi-product) or buy now (single product)?
- Guest checkout or account required?
- Saved cart (persists after session)?
- Checkout steps (how many pages)
- Address autocomplete?
- Order summary page

### 38. Shipping & Delivery
- Physical or digital products?
- Who handles shipping? (Client or courier)
- Shipping zones (Nigeria only, international)
- Shipping cost calculation (flat rate, by weight, by location)
- Delivery time estimates shown to customer?
- Order tracking integration?

### 39. Discount & Promotions
- Discount codes / promo codes
- Percentage vs fixed amount discounts
- Minimum order value for discount
- Expiry dates on codes
- Flash sales / limited time offers
- Loyalty program?

### 40. Order Management
- Order statuses (pending, confirmed, shipped, delivered, cancelled)
- Who gets notified and how (email, WhatsApp, both)
- Order history for customers
- Admin order management panel
- Refund and cancellation flow
- Returns process

### 41. CMS Integration
- Is there a CMS? (Sanity, Contentful, none)
- Who updates content? (Developer or client)
- What content is editable? (Products, blog, banners, homepage)
- Content preview before publishing?

### 42. Reviews & Testimonials
- Customer reviews on products?
- Moderation required?
- Star ratings?
- Photo reviews?
- Testimonials section (curated, not from customers)

---

## SECTION C — WEB APP SPECIFIC

### 43. Authentication & Authorization
- Auth provider (Supabase Auth, NextAuth, Clerk)
- Login methods (email/password, Google, GitHub, magic link)
- Role-based access control (admin, user, moderator)
- Protected route strategy
- Session management
- Password reset flow
- Email verification flow

### 44. User Management
- User profiles (what fields)
- Avatar upload
- Account settings page
- Account deletion (soft or hard)
- Admin panel for managing users
- User search and filtering (admin side)

### 45. Onboarding Flow
- First-time user experience
- Empty states (what user sees with no data)
- Guided tour or tooltips?
- Welcome email sequence
- Progress indicators

### 46. Dashboard & Data Visualization
- What charts are needed? (bar, line, pie, area)
- Chart library (Recharts, Chart.js, D3)
- Date range filtering
- Data export (CSV, PDF)
- Real-time updates on dashboard?
- Pagination on tables

### 47. Real-time Features
- What needs live updates? (notifications, chat, dashboard)
- Supabase Realtime, websockets, or polling?
- What triggers real-time events?
- Conflict handling when two users edit same data?

### 48. Notification System
- In-app notifications
- Email notifications (which events trigger emails)
- Push notifications (mobile/PWA)
- Notification preferences (user can turn off)
- Notification history/inbox

### 49. Multi-tenancy
- Is this one app serving multiple organizations?
- Row-level data isolation (Supabase RLS)
- Subdomain per tenant?
- Tenant-specific settings and branding?
- MUST be decided before any database design

### 50. File Management
- Upload functionality (what file types)
- Storage provider (Supabase Storage, Cloudinary, S3)
- File size limits
- File type restrictions
- Virus scanning?
- File deletion (when user deletes, is file removed from storage?)

### 51. Search & Filtering
- Global app search?
- Per-table filtering
- Supabase full-text search or Algolia?
- Filter persistence (saved after page reload?)
- Sort options

### 52. Audit Logs & Activity History
- Who did what and when
- Which actions are logged?
- How long are logs retained?
- Who can see the logs? (admin only, all users)
- Important for apps handling money or sensitive data

### 53. Import & Export
- Can users import data? (CSV upload)
- Can users export data? (CSV, PDF, Excel)
- Bulk operations (select all, delete all, update all)
- Data portability (user can download all their data)

### 54. Subscription & Feature Gating
- Which features are free vs paid?
- How is entitlement checked? (on every request or cached)
- What happens when subscription expires?
- Grace period after expiry?
- Upgrade/downgrade flow

### 55. Settings & Configuration
- User-level settings (preferences, notifications, theme)
- App-wide settings (admin configures)
- Feature flags (turn features on/off without deploying)
- Where do settings persist? (database, never localStorage)

### 56. Admin Panel
- Separate from user-facing app or embedded?
- Who has admin access?
- What can admin do? (manage users, view logs, configure settings)
- Admin-only routes protection

### 57. API Design (if exposing API)
- REST or GraphQL?
- Versioning strategy (/api/v1/)
- Authentication for API (Bearer token, API key)
- Rate limiting
- API documentation (Swagger, Postman collection)
- If mobile app will consume this later — design for it now

### 58. Background Jobs & Queues
- What tasks run in background? (emails, file processing, reports)
- Job queue tool (Inngest, Bull, Supabase Edge Functions)
- Retry logic on failure
- Job monitoring

### 59. Soft Delete vs Hard Delete
- When user deletes something, is it gone forever or recoverable?
- This decision affects the entire database schema
- Soft delete adds deleted_at column — data stays but is hidden
- Hard delete removes permanently

### 60. Collaboration Features
- Multiple users editing same data?
- Presence indicators (who is online)?
- Conflict resolution strategy?
- Locking (only one user can edit at a time)?
- Comments on records?

### 61. Webhooks (Outgoing)
- Does your app need to notify external services?
- What events trigger webhooks?
- Payload structure
- Retry logic on failure
- Webhook secret for verification

### 62. Timezone & Localization
- Dates stored in UTC in database (always)
- Dates displayed in user's local timezone
- Currency display per user location
- Number formatting (comma vs period for decimals)

### 63. Rate Limiting & Abuse Prevention
- API rate limiting (Upstash Redis)
- Form submission throttling
- Login attempt limiting
- Bot protection (Turnstile, hCaptcha)
- IP blocking strategy

### 64. Multi-step Flows & Wizards
- Any complex multi-step processes? (checkout, onboarding, setup)
- Progress saved between steps?
- Back button behavior
- Validation per step or at end?

---

## SECTION D — MOBILE / DESKTOP APP SPECIFIC

### 65. Platform Targets
- iOS, Android, Desktop (Windows/Mac/Linux), or all?
- Native or hybrid? (Capacitor, Tauri, Expo)
- Minimum OS versions supported?

### 66. App Store & Distribution
- App Store (Apple) submission plan
- Play Store (Google) submission plan
- Developer account setup
- App signing and certificates
- Review process timeline (Apple takes 1-3 days)

### 67. Push Notifications (Mobile)
- Native push notifications (FCM for Android, APNs for iOS)
- Permission request flow (when and how to ask)
- Notification categories
- Deep linking from notification

### 68. Device Features
- Camera access needed?
- Microphone access?
- GPS/Location?
- Contacts access?
- Biometric authentication (fingerprint, Face ID)?
- Each requires explicit permission handling

### 69. Offline Mode (Mobile)
- What works without internet?
- Local data storage (SQLite, AsyncStorage)
- Sync strategy when connection returns
- Conflict resolution on sync
- Critical for Nigerian context

### 70. App Updates
- Force update strategy (block old versions)
- Over-the-air updates (Expo OTA, CodePush)
- Migration strategy for breaking changes
- Changelog shown to user on update?

### 71. Deep Linking
- URL scheme for opening specific screens from outside
- Universal links (iOS) and App Links (Android)
- Sharing content that opens in app

### 72. Performance (Mobile Specific)
- App startup time target
- Memory usage limits
- Battery usage optimization
- Large list rendering (FlatList, virtualization)
- Image caching strategy

---

## SECTION E — UNIVERSAL ADVANCED AREAS

### 73. Progress Tracking (Build Time)
- Before any multi-step task, write a checklist to file
- Every completed step gets marked
- If session dies, reopen and continue from last checkpoint
- Never lose build progress

### 74. Session Recovery
- After any interruption, first action is reload all MD/rule files
- Write session log after every meaningful action
- Log contains: what was done, what's next, decisions made
- Session is always resumable

### 75. Constraint Identification
- Before planning, surface all real-world constraints
- Budget limits, hosting limits, third party API restrictions
- Nigerian context constraints (payment providers, connectivity)
- Hardware constraints (client's device capabilities)
- Identify constraints BEFORE architecture decisions

### 76. Scalability Planning
- What is the expected traffic at launch?
- When does the current stack break?
- What is the upgrade path when you outgrow it?
- Database indexing strategy for growth
- CDN strategy

### 77. Security
- HTTPS enforced everywhere
- Input sanitization (prevent XSS, SQL injection)
- CORS configuration
- Auth token storage (httpOnly cookies, not localStorage)
- Dependency vulnerability scanning
- What data is sensitive and how is it protected?

### 78. Landing Page vs App Shell
- Even web apps have a public-facing landing page
- Different caching rules for public vs authenticated pages
- Different SEO requirements
- Separate deployment or same codebase?

### 79. Design Tokens & Theming
- CSS variables for all design values
- Light and dark mode token sets
- How themes switch (class on html, CSS media query)
- Token naming convention (--color-primary, not --blue)

### 80. Third Party Integrations
- Email (Resend, SendGrid)
- SMS (Termii for Nigeria, Twilio)
- Maps (Google Maps, Mapbox)
- Analytics (Posthog, GA4)
- Social login (Google, GitHub)
- Customer support chat (Crisp, Intercom)
- Each integration: register account, get keys, add to .env.example BEFORE build starts

### 81. Load & Stress Testing
- What is the expected concurrent user load at launch and in 6 months?
- What is the acceptable response time under load (e.g., < 2 seconds)?
- What load testing tool will be used? (k6, Artillery, Locust)
- What is the stress testing plan to find the breaking point?
- Who runs these tests and when?

### 82. NDPR Compliance (Nigeria)
- Explicit consent required before collecting personal data
- Privacy policy in plain language
- Data Processing Agreement with third parties
- Right to access, rectify, erase personal data
- Data Protection Officer (DPO) contact
- Cross-border data transfer rules
- Data retention schedule
- Children's data protection (under 18)

---

## SECTION F — MODERN AREAS (NEW)

### 83. AI Features
- LLM integration (OpenAI, Anthropic, local models)
- Embeddings & vector search (pgvector, Pinecone)
- RAG (Retrieval-Augmented Generation) pipeline
- Streaming responses (SSE, WebSocket)
- Token usage monitoring & cost limits
- AI safety: prompt injection protection, output validation
- Model fallback strategy when primary model is down
- User-facing AI features (chat, suggestions, summaries)
- AI usage logging for audit

### 84. Realtime & Live Updates
- WebSocket connection strategy (Supabase Realtime, Socket.io, Pusher)
- Presence indicators (who is online)
- Live cursors / collaborative editing
- Conflict resolution (CRDT, last-write-wins, manual)
- Reconnection & backoff strategy
- Heartbeat/ping mechanism
- Scaling realtime across multiple servers
- Fallback to polling when WebSocket fails

### 85. Observability
- Structured logging (JSON logs, correlation IDs)
- Distributed tracing (OpenTelemetry, Datadog APM)
- Metrics collection (Prometheus, Grafana)
- Log aggregation (Logtail, Better Stack, self-hosted Loki)
- Alerting rules & escalation policy
- Dashboard for system health
- SLO/SLI definitions (uptime, latency, error rate)
- Incident response runbook

### 86. Edge Functions
- Edge runtime (Cloudflare Workers, Vercel Edge, Deno Deploy)
- Geographic distribution strategy
- Edge vs origin: what runs where?
- Edge caching strategy
- Edge database (Turso, Cloudflare D1, Neon edge)
- Cold start optimization
- Limitations: no Node.js APIs, smaller memory
- A/B testing at the edge

### 87. Type Safety
- TypeScript strict mode enabled
- No `any` types allowed
- Runtime validation (Zod schemas at API boundaries)
- Schema-first API design (OpenAPI → types)
- Database types generated from schema (Prisma, Drizzle, Supabase types)
- Type-safe environment variables (t3-env or similar)
- Branded types for IDs (e.g. `UserId`, `OrderId`)
- Type tests (tsd, expect-type)

### 88. Privacy & Consent
- Cookie consent banner (granular: necessary, analytics, marketing)
- Consent management platform (Cookiebot, Termly, custom)
- Data Subject Rights flow (access, deletion, portability)
- Data Processing Records (Article 30 of GDPR)
- Privacy by Design in feature development
- Data minimization (only collect what's needed)
- Anonymization & pseudonymization
- Right to be forgotten — automated deletion flow

---

## SUMMARY COUNT

| Section | Areas | Topic |
|---|---|---|
| A — All Projects | 01 — 33 | Every project must consider |
| B — E-Commerce | 34 — 42 | Online shops only |
| C — Web Apps | 43 — 64 | SaaS, dashboards, platforms |
| D — Mobile/Desktop | 65 — 72 | Native apps |
| E — Universal Advanced | 73 — 82 | Always relevant, often missed |
| F — Modern (NEW) | 83 — 88 | AI, realtime, observability, edge, types, privacy |
| **Total** | **88 Areas** | |

---

*Last updated: July 2026*
*WebForge — Victor Makuo*
