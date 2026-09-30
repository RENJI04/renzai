# Risk profile and scoring

The system-owned immutable profile `renzai-v1`, version 1, is seeded with the Phase 3 weights. The profile uses formula version `1.0.0`; traffic and future false-positive labels cannot mutate it.

For each finding, `raw = (weight * confidence + 50) // 100`. Only the strongest contribution in each Phase 6 overlap group is retained. The two highest retained, non-overlapping contributions from different categories may add `min(25, second_raw // 2)`; no later contribution affects the score. Output `secrets.api_key` findings at confidence 90 or above apply an 80-point floor. The final score is capped at 100.

Bands are low 0–24, medium 25–49, high 50–74, critical 75–100. Analysis confidence is the confidence of the strongest retained contribution—not a probability that content is malicious. Risk never varies implicitly by environment.
