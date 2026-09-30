# Configuration foundation

`renzai.core.config.Settings` is typed, validated and safe by default. It provides concrete APP, DATABASE, REDIS, LOGGING, CORS, PRIVACY, RETENTION, SESSION, FEATURE_FLAGS and CELERY values plus typed deferred markers for the remaining Phase 3 configuration groups. `.env.example` uses placeholders only, and `.gitignore` excludes all local variants except the example.

Production requires HTTPS public URL, rejects wildcard credentialed CORS and rejects unsafe inspection override. Logging redacts known secret/body keys regardless of development text or production JSON rendering.
