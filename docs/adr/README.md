# Architecture decision records

Short records of the choices that are not obvious from reading the code, and would
otherwise be re-litigated or accidentally undone. Several were made on a predecessor
project with the same architecture and carried over with the reasoning intact.

| # | Decision |
| --- | --- |
| [0001](0001-server-rendered-not-spa.md) | Server-rendered FastAPI + HTMX, not a static SPA |
| [0002](0002-visible-navigation.md) | At most four visible links, nothing hidden |
| [0003](0003-asset-cache-versioning.md) | Content-versioned asset URLs and cache headers |
| [0004](0004-deployment.md) | Docker Compose + Caddy on a single droplet |
| [0005](0005-continuous-deployment.md) | Push to main deploys the image the gate tested |
| [0006](0006-dependency-hygiene.md) | Dependencies audited weekly and pinned exactly |
| [0007](0007-production-runtime-limits.md) | Production containers are bounded |
| [0008](0008-compose-project-isolation.md) | The Compose project name is an isolation boundary |
| [0009](0009-base-images-pinned-by-digest.md) | Base images pinned by digest, each with a watcher |
| [0010](0010-two-hosts.md) | A development host serves the working tree; production serves `main` |
| [0011](0011-private-repository.md) | The repository is private; production borrows the deploy job's token |
| [0012](0012-photos.md) | Photo originals tracked beside the app; only derivatives served |
| [0013](0013-owner-assistant-account.md) | The owner's assistant is an unprivileged account; the ACLs are the boundary |

Format: context, decision, consequences. Keep them short; if one needs reversing, add a
new record that supersedes it rather than rewriting history.
