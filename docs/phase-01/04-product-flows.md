# Primary product flows

## A. Analyze-only mode

`AI application → Analyze API → Security detectors → Risk engine → Policy engine → Allow / Flag / Block / Redact`

The client submits bounded input and application credentials. Renzai normalizes the content, runs deterministic detectors and heuristics, calculates a score, severity and confidence, and evaluates ordered enabled policies. The response returns structured findings, contributions, explanation, and action. No external provider is needed. Logged content follows the application storage policy.

## B. Gateway mode

`AI application → Gateway → Input analysis → Policy decision → optional AI provider → Output analysis → Policy decision → application`

The gateway authenticates the caller, scans input, and applies input policy before forwarding. When allowed, it forwards only to a configured provider under timeout and URL-safety controls. It scans the provider response and applies output policy before returning it. Optional AI-intelligence failure does not stop deterministic core operation. If security inspection cannot produce a valid enforcement decision, staging and production fail closed by default; development may explicitly select a less restrictive behavior. If provider forwarding fails, Renzai returns a stable provider/gateway failure response and never bypasses security controls.

## C. Security Playground

An authorized dashboard user enters a prompt or response and selects applicable context. Renzai returns findings, individual detector outcomes, severity, 0–100 risk score, confidence, policy outcome, contribution breakdown, and a safe explanation. Unless changed by authorized configuration, content uses redacted storage, safe content is not persisted, and retention defaults to 30 days.

## D. Incident investigation

`Threat detected → privacy-aware event log → incident if policy/configuration requires → investigation → optional AI analysis → resolved / false positive`

An incident includes application and environment context, findings, action taken, timeline, status, assignee, and comments. An analyst can request optional AI-produced analysis only after deterministic evidence is visible and distinctly labelled. Status changes and security-sensitive actions are audited.

## E. Application onboarding

`Register/login → organization → application → environment → application API key → integration`

The user creates an organization, creates an application and one or more development, staging, or production environments, generates a scoped application API key shown once, and integrates Analyze API or Gateway. Key material is never retrievable after creation.
