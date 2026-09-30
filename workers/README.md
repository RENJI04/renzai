# Worker foundation

`renzai_worker` contains only Celery configuration and a side-effect-free diagnostic task. It uses JSON serializers, UTC and bounded task defaults. Product jobs (AI, webhook, retention and notification) are deliberately deferred. Worker entry points set `PYTHONPATH=apps/api/src;workers/src` on Windows or the equivalent shell path on POSIX.
