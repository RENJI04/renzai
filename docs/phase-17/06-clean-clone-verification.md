# Clean-room release verification

The blocking clean-room gate must use a fresh export or clone of the **final candidate working
tree**, without its existing virtualenv, Node modules, local environment, build output, or data
volumes. The public [Quick Start](../quick-start.md) is the test script; port and Compose project
names may be changed only to isolate the disposable test stack from an existing local stack.

Record dependency installation, environment preparation, Compose build, migration, health/readiness,
registration, demo seed, key creation, Analyze, Attack Lab, reference app, incident inspection, and
clean shutdown. A failed or incomplete step must be reported as a blocker, not a guarantee.

The source-only export contained 602 candidate files and no `.git`, virtualenv, Node modules,
local environment, or pre-existing data volume. Dependency installation succeeded from the
export: Compose rebuilt API, worker, web, and migration images with frozen pnpm dependencies,
and the Python SDK/reference-app dependencies installed into a new isolated virtualenv.
`prepare_demo_env.py` created a local ignored environment. To isolate this disposable
rehearsal from the existing demo stack, it used a unique Compose project and loopback HTTP and
Grafana ports.

The first Compose configuration attempt exposed a Quick Start defect: `--env-file` alone did
not set the `RENZAI_ENV_FILE` variable used by the base Compose service's `env_file`. The
public Quick Start now exports that variable, and `smoke_compose.py` propagates the selected
environment file to child Compose commands. With this correction, Compose configuration,
all runtime starts, migration, API health/readiness, web/Nginx, worker, PostgreSQL, Redis,
Prometheus, exporters, OTel collector, Grafana, and the observability smoke check passed.

The browser-equivalent HTTP workflow registered a synthetic user, bootstrapped a session,
seeded three applications, nine environments, 28 analyses, eight incidents, eight provider-call
records, and one historical AI result, issued an application key with CSRF protection, inspected
safe and attack requests, retrieved the incident queue and detail, and passed all 25 curated
Attack Lab cases. The provider-free reference app loaded and returned a synthetic provider
response for safe input while withholding that path for a review-required attack.

The disposable stack was subsequently rebuilt after the Python and Node base-image security
updates. That rebuild exposed a real proxy defect: a still-running Nginx process retained old
container addresses and initially returned 502 after API/web replacement. Nginx now resolves
the Docker service names dynamically. A regression test and live test confirmed that the API
and web containers can be forcibly recreated while the Nginx container stays unchanged; the
complete Compose smoke check then passed. All eight seeded incidents remained in PostgreSQL
after the restart. The isolated Compose project was shut down cleanly with zero containers
running; named data volumes were preserved. The rehearsal is local verification, not production
certification.
