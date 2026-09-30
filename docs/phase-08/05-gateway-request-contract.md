# Gateway request contract

`POST /v1/chat/completions` uses the environment Application API key and derives organization, application, environment, key, and provider scope server-side. The request body cannot select tenancy.

Allowed fields are `model`, `messages`, optional `stream=false`, `temperature` (0–2), `top_p` (>0–1), `max_tokens` (1–4096 and provider ceiling), `stop` (one bounded string or 1–4 bounded strings), `presence_penalty` and `frequency_penalty` (-2–2), and signed-int32 `seed` when the provider declares support. `model` must exactly match the active configured provider model.

Messages contain 1–32 items. Roles are only `system`, `user`, or `assistant`; content is nonblank text. An ASGI middleware enforces the 96-KiB body default before JSON parsing; combined message text is limited to 64 KiB, and model/provider responses use configured bounds. Unknown fields are rejected rather than stripped.

Unsupported fields include streaming, tools, tool choice, functions, function calls, multimodal content, content-part arrays, `response_format`, `stream_options`, `max_completion_tokens`, and arbitrary passthrough data. This is a documented OpenAI-style subset, not full OpenAI compatibility.
