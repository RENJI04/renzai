# Normalization pipeline

Normalization version `1.0.0` is deterministic and offline. Processing first rejects content above the configured 32 KiB UTF-8 default (128 KiB hard configuration ceiling), then applies per-character Unicode NFKC, removes known zero-width characters while recording an obfuscation indicator, and collapses whitespace. The primary candidate keeps a normalized-character-to-original-index map.

Explicit, one-pass candidates cover percent decoding, HTML entities, `\\uXXXX` escapes, and printable UTF-8 Base64. Candidate count defaults to eight, each candidate is at most 4,096 characters, decoded expansion is capped at four times its source, and decode depth is one. A transform never recursively feeds another transform. Invalid encodings are ignored safely; they do not abort otherwise valid inspection.

Decoded candidates may be scanned by the same detector rules. Sensitive matches in transformed candidates cause conservative whole-value typed redaction for stored REDACTED content, avoiding persistence of an encoded original secret. Every transform consumes the fixed candidate budget. These controls prevent unbounded recursion, decompression behavior, and candidate explosion.
