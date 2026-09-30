# Policy condition grammar

A version contains one flat `all` or `any` group with 1–20 conditions. There are no nested groups, regexes, scripts, arbitrary database queries, or external calls.

Allowed facts are phase, category set, detector ID set, risk score, final severity, confidence band, application ID, environment type, and source. Operators are limited per fact to `equals`, `in`, `greater_or_equal`, `less_or_equal`, and `contains_category`. Values are bounded and type/enum validated; `in` accepts 1–20 values.

Evaluation receives an immutable fact object assembled after successful detection/risk evaluation. Invalid stored snapshots cause `inspection_failure`; they never degrade to allow.
