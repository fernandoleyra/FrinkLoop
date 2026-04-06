# Project Conventions — Applied to Every Project

## Language Selection
- Web API: TypeScript + Node.js (Hono or Fastify)
- Python service: Python 3.11+ with uv for deps
- CLI tool: TypeScript with tsx
- Frontend: React + TypeScript + Tailwind
- Default to the language the human specifies. If unspecified: TypeScript.

## File Naming
- kebab-case for files: user-service.ts, auth-middleware.ts
- PascalCase for classes and React components
- camelCase for functions and variables
- SCREAMING_SNAKE for env var names

## Project Structure (enforced by template)
src/
  core/         — business logic, no framework dependencies
  api/          — HTTP handlers and routes
  services/     — external integrations (DB, APIs, queues)
  utils/        — pure helper functions
  types/        — TypeScript types and Zod schemas
tests/
  unit/         — test core/ in isolation
  integration/  — test with real dependencies (docker-compose)
docs/
scripts/
  test.sh       — runs all tests
  lint.sh       — runs linter
  build.sh      — builds for production
  dev.sh        — starts dev server

## Git Conventions
- Commit after every task that passes QA
- Message format: <type>(<scope>): <description>
  types: feat, fix, refactor, test, docs, chore
- Branch per milestone: milestone/1-core-crawler
- Never commit to main directly

## Environment Variables
- All config via environment variables
- .env.example committed with all vars listed (no values)
- .env never committed (in .gitignore always)

## Error Handling
- Never swallow errors silently
- Always include context: throw new Error(`Failed to fetch URL ${url}: ${cause}`)
- User-facing errors: human-readable message + error code
- Internal errors: full stack trace in logs

## Testing Requirements
- Every public function has at least one unit test
- Every API endpoint has at least one integration test
- Tests must be deterministic (no random, no time-dependent)
- Minimum coverage gate: 70% (enforced in CI)
