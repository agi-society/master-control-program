# AGI Society Work MVP

A deliberately small internal work system seeded with the AGI Society commitments supplied during design.

## Run locally

```bash
docker compose up --build -d
```

Open: http://localhost:8000

On a brand-new database you will be redirected to `/setup/` to create the **first administrator**. After that:

- use the normal app at `/`
- create/edit users and Person profiles at `/admin/`
- link a Django User to a Person so **My Work** defaults to that person
- API root: `/api/`
- CSV export: `/api/export/work.csv`
- JSON snapshot: `/api/export/snapshot.json`

Stop:

```bash
docker compose down
```

Reset everything, including Postgres data:

```bash
docker compose down -v
```


## Current MVP interaction model

- `/` is **My Work**: the visual work map filtered by assignee, with an optional **Due by** date. It defaults to the Person linked to the logged-in account.
- `/board/` supports native drag/drop both between status columns and within a column; changes persist immediately.
- Work items have an editable muted color palette. Child work inherits its parent color unless explicitly overridden. The same color is used on My Work, Board, and work details.
- `/my-work/` is kept only as a compatibility redirect to `/`; the old list-style My Work screen is removed.

## TDD loop

The intended development loop is:

1. Write a failing domain/integration test.
2. Run `docker compose run --rm web python manage.py test`.
3. Implement the smallest behavior to pass it.
4. Refactor while tests remain green.
5. Test the user workflow in the browser.

The existing tests cover:

- invalid temporal ranges
- invalid self-dependencies
- first-run admin bootstrap
- seeded work presence + idempotence
- authenticated API access
- CSV export infrastructure
- My Work assignee/due-date filtering
- project color inheritance/override
- board status moves and within-column ordering
- CSS/JavaScript static asset discovery

### Run tests locally without starting the server

```bash
docker compose run --rm web python manage.py test
```

## Why auth is intentionally simple

Django's built-in `User` is the login identity. `Person` is the durable organizational identity and has an **optional one-to-one link** to `User`.

That means work always points to `Person`, never directly to login accounts. When OAuth/OIDC is introduced later, the authentication backend can change while Person IDs, work ownership, completion history, and collaborations remain intact.

For the MVP, the first user is created at `/setup/`; that admin can create more accounts using Django Admin.

## Seed assumptions

The seed command is idempotent and uses title as the initial matching key. It contains the work supplied from Monday.com plus the additional work specified in chat.

Dates explicitly supplied or previously fixed operationally are included (Boston Aug 27, Dubai Sep 8, Mauritius Sep 11). "Starting Monday" is represented as 2026-08-17. Items without a reliable deadline remain undated rather than inventing one.

## Deliberately not built yet

- Monday synchronization UI
- bulk edit UI
- export UI (endpoints already exist)
- OAuth/OIDC
- complex permissions
- notifications
- file hosting
- S0/MCP adapter
- drag/drop timeline editing (Board drag/drop is implemented)
- dedicated dependency graph visualization (dependencies themselves are editable now)

The schema/API/activity model are intended to make those additions incremental rather than architectural rewrites.

## Static asset verification

The container now fails startup if the primary stylesheet is not collected. After startup, this URL should return CSS (HTTP 200):

    http://localhost:8000/static/work/app.css

Regression tests also verify that Django can discover the stylesheet:

    docker compose run --rm web python manage.py test work.tests.test_static_assets

## Private work and sharing

Work now has two visibility modes:

- **Organization** — visible to authenticated users.
- **Private** — visible only to the Person who created it and People explicitly selected under **Share private work with**.

Private work remains owned by its creator. Sharing grants access; it does not transfer ownership. This is intended to let each person keep personal work on the same board while selectively granting other account access.

The privacy rule is enforced in the backend through `Work.objects.visible_to(user)` and is applied to the Work Map, Board, direct detail URLs, board drag/drop mutations, REST API, CSV/JSON exports, activity, and dependencies. A dependency is returned only when both work items are visible to the requesting user; there are no hidden/private blocker placeholders.

To use other profiles later, create a normal Django User + Person named e.g. `User x`, then explicitly share selected private work with that Person. Users can authenticate separately against the same API while also owning normal organization work.

## DigitalOcean / Git + Docker deployment

The repository is ready for the simple deployment loop: clone/pull on a droplet and rebuild Compose.

First deployment:

```bash
git clone <your-repository-url> agis-work-mvp
cd agis-work-mvp
cp .env.example .env
# edit .env with the real domain, DB password and Django secret

docker compose up --build -d
```

Routine deploy after pushing changes:

```bash
cd agis-work-mvp
git pull --ff-only
docker compose up --build -d
```

Inspect status/logs:

```bash
docker compose ps
docker compose logs -f web
```

Run migrations/tests manually if desired (startup already runs migrations):

```bash
docker compose run --rm web python manage.py test
```

The Postgres data lives in the named `pgdata` Docker volume, so a normal `docker compose down` / rebuild does not delete application data. Do **not** use `docker compose down -v` on the hosted system unless you intentionally want to destroy the database.

For HTTPS behind Caddy/Nginx, set the production values in `.env`:

```text
DJANGO_DEBUG=0
ALLOWED_HOSTS=work.yourdomain.org
CSRF_TRUSTED_ORIGINS=https://work.yourdomain.org
TRUST_X_FORWARDED_PROTO=1
SESSION_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1
```

The application container still listens on port 8000; the reverse proxy can terminate TLS and forward to it.
