# Container architecture

The API, worker, and web application use separate production images. Python images use a dependency-build stage and a minimal Python 3.13 runtime; the web image uses pnpm in a build stage and Next.js standalone output in a non-root Node 22 runtime. Runtime containers do not contain repository tests or development servers.

API and worker run as UID/GID 10001. Web runs as the image-provided `node` user. Compose gives application containers read-only root filesystems, writable `/tmp`, dropped capabilities, `no-new-privileges`, an init process, and bounded health checks. The worker uses the Celery solo pool in each container so its in-process metrics endpoint reflects the single worker process; throughput is increased with replicas rather than hidden child processes.

Image tags are deliberately explicit. They are not immutable digests, so operators should mirror and digest-pin approved images for higher-assurance production environments. CI builds the three product images but never publishes them.
