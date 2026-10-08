# Renzai Attack Lab

Attack Lab is a safe, synthetic demonstration corpus for Renzai's eleven deterministic V1 threat
categories. It is not an exploitation framework, a universal detection benchmark, or proof that
Renzai prevents every attack. Each category has a malicious example and a benign control; bounded
encoding cases cover Base64, percent encoding, HTML entities, Unicode normalization, and zero-width
characters without executing payloads.

Start Renzai, create an application key, install the local Python SDK, then run:

```bash
python -m pip install -e ./packages/python-sdk
export RENZAI_BASE_URL=http://localhost:8080
export RENZAI_API_KEY='<application-key-from-Renzai>'
python examples/attack-lab/run.py
python examples/attack-lab/run.py --json
```

In PowerShell use `$env:RENZAI_BASE_URL` and `$env:RENZAI_API_KEY`. The runner never prints scenario
inputs or credentials. Results assert category presence for malicious/boundary cases and the absence
of findings for controls. Actions are shown but not treated as invariant because active tenant policy
determines enforcement. See [the threat catalog](../../docs/security/threat-catalog.md) for limits.
