# Attack Lab

[Attack Lab](../../examples/attack-lab/README.md) provides JSON source scenarios and a Python SDK
runner. Every frozen category has a malicious sample and benign control. Base64, percent encoding,
HTML entities, Unicode/zero-width normalization are represented without executable payloads.

Expected results assert category presence or no finding. The runner displays the actual action but
does not make policy-dependent exact-action values a brittle invariant. Inputs and credentials are
not printed. The corpus is a curated deterministic demonstration, not an offensive framework or a
claim of universal attack detection.
