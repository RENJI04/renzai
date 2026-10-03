import { RenzaiError, RenzaiProtocolError, errorTypes } from "./errors.js";
import type {
  AIIntelligenceResult,
  AnalyzeResult,
  AnalyticsDashboard,
  ChatCompletion,
  Finding,
  Incident,
  IncidentPage,
  JsonObject,
  PolicyDecision,
} from "./types.js";

const DIRECTIONS = ["input", "output"] as const;
const SEVERITIES = ["low", "medium", "high", "critical"] as const;
const ACTIONS = ["allow", "flag", "block", "redact", "require_review"] as const;
const CATEGORIES = [
  "prompt_injection",
  "instruction_override",
  "system_prompt_extraction",
  "jailbreak",
  "role_manipulation",
  "encoded_obfuscated",
  "secret_exposure",
  "pii_exposure",
  "suspicious_url",
  "tool_manipulation_indicator",
  "data_exfiltration_indicator",
] as const;
const INCIDENT_STATUSES = [
  "open",
  "investigating",
  "resolved",
  "ignored",
  "false_positive",
] as const;
const INCIDENT_SOURCES = [
  "manual",
  "gateway",
  "analyze",
  "playground",
] as const;
const AI_TASKS = [
  "incident_summary",
  "attack_explanation",
  "mitigation_suggestion",
  "policy_suggestion",
] as const;
const AI_STATUSES = ["pending", "running", "completed", "failed"] as const;
const DISCLOSURE_MODES = ["metadata_only", "redacted", "full"] as const;

export function asObject(value: unknown, label = "response"): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw protocolError(`Renzai returned a malformed ${label}.`);
  }
  return value as JsonObject;
}

function protocolError(
  message: string,
  requestId?: string,
  statusCode?: number,
): RenzaiProtocolError {
  return new RenzaiProtocolError(message, {
    code: "protocol_error",
    ...(requestId === undefined ? {} : { requestId }),
    ...(statusCode === undefined ? {} : { statusCode }),
  });
}

function stringValue(data: JsonObject, key: string): string {
  const value = data[key];
  if (typeof value !== "string")
    throw protocolError(`Renzai response is missing ${key}.`);
  return value;
}

function numberValue(data: JsonObject, key: string): number {
  const value = data[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw protocolError(`Renzai response is missing ${key}.`);
  }
  return value;
}

function booleanValue(data: JsonObject, key: string): boolean {
  const value = data[key];
  if (typeof value !== "boolean")
    throw protocolError(`Renzai response is missing ${key}.`);
  return value;
}

function enumValue<const Values extends readonly string[]>(
  data: JsonObject,
  key: string,
  values: Values,
): Values[number] {
  const value = stringValue(data, key);
  if (!values.includes(value)) {
    throw protocolError(`Renzai response contains an invalid ${key}.`);
  }
  return value;
}

function stringArray(data: JsonObject, key: string): string[] {
  const value = data[key];
  if (!Array.isArray(value)) {
    throw protocolError(`Renzai response is missing ${key}.`);
  }
  const result: string[] = [];
  for (const item of value as unknown[]) {
    if (typeof item !== "string") {
      throw protocolError(`Renzai response is missing ${key}.`);
    }
    result.push(item);
  }
  return result;
}

function trueValue(data: JsonObject, key: string): true {
  if (!booleanValue(data, key)) {
    throw protocolError(`Renzai returned an invalid ${key} label.`);
  }
  return true;
}

function objectArray(data: JsonObject, key: string): JsonObject[] {
  const value = data[key];
  if (!Array.isArray(value))
    throw protocolError(`Renzai response is missing ${key}.`);
  return value.map((item) => asObject(item, key));
}

export function requestId(headers: Headers): string | undefined {
  return (
    headers.get("x-renzai-request-id") ??
    headers.get("x-request-id") ??
    undefined
  );
}

export function throwServerError(payload: unknown, response: Response): never {
  const outer = asObject(payload, "error response");
  const envelope = asObject(outer.error, "error envelope");
  const code = envelope.code;
  const message = envelope.message;
  if (typeof code !== "string" || typeof message !== "string") {
    throw protocolError(
      "Renzai returned a malformed error response.",
      requestId(response.headers),
      response.status,
    );
  }
  const ErrorType = errorTypes[code] ?? RenzaiError;
  const bodyRequestId =
    typeof envelope.request_id === "string" ? envelope.request_id : undefined;
  const details =
    typeof envelope.details === "object" &&
    envelope.details !== null &&
    !Array.isArray(envelope.details)
      ? (envelope.details as JsonObject)
      : undefined;
  const serverRequestId = bodyRequestId ?? requestId(response.headers);
  throw new ErrorType(message, {
    code,
    ...(serverRequestId === undefined ? {} : { requestId: serverRequestId }),
    ...(details === undefined ? {} : { details }),
    statusCode: response.status,
  });
}

export function parseAnalyze(
  payload: unknown,
  responseRequestId?: string,
): AnalyzeResult {
  const data = asObject(payload, "Analyze response");
  const rawFindings = data.findings;
  if (!Array.isArray(rawFindings))
    throw protocolError("Renzai returned malformed findings.");
  const findings: Finding[] = rawFindings.map((item) => {
    const row = asObject(item, "finding");
    const metadata = asObject(row.metadata, "finding metadata");
    return {
      findingId: stringValue(row, "finding_id"),
      detectorId: stringValue(row, "detector_id"),
      detectorVersion: stringValue(row, "detector_version"),
      rulesetVersion: stringValue(row, "ruleset_version"),
      category: enumValue(row, "category", CATEGORIES),
      direction: enumValue(row, "direction", DIRECTIONS),
      severity: enumValue(row, "severity", SEVERITIES),
      confidence: numberValue(row, "confidence"),
      evidence: asObject(row.evidence, "finding evidence"),
      safeExplanation: stringValue(row, "safe_explanation"),
      metadata: Object.fromEntries(
        Object.entries(metadata).map(([key, value]) => [key, String(value)]),
      ),
    };
  });
  const rawPolicy = asObject(data.policy_decision, "policy decision");
  const redactionTargets = stringArray(rawPolicy, "redaction_targets");
  const evaluatedPolicyVersions = objectArray(
    rawPolicy,
    "evaluated_policy_versions",
  );
  const scopeWinners = objectArray(rawPolicy, "scope_winners");
  const policyMatch = rawPolicy.policy_match;
  const policyDecision: PolicyDecision = {
    policyDecisionId: stringValue(rawPolicy, "policy_decision_id"),
    rationaleCode: stringValue(rawPolicy, "rationale_code"),
    redactionTargets,
    policyMatch:
      policyMatch === null ? null : asObject(policyMatch, "policy match"),
    evaluatedPolicyVersions,
    scopeWinners,
  };
  const result: AnalyzeResult = {
    analysisId: stringValue(data, "analysis_id"),
    eventId: stringValue(data, "event_id"),
    timestamp: stringValue(data, "timestamp"),
    direction: enumValue(data, "direction", DIRECTIONS),
    source: stringValue(data, "source"),
    safe: booleanValue(data, "safe"),
    noDetectedThreat: booleanValue(data, "no_detected_threat"),
    action: enumValue(data, "action", ACTIONS),
    riskScore: numberValue(data, "risk_score"),
    severity: enumValue(data, "severity", SEVERITIES),
    confidence: numberValue(data, "confidence"),
    riskProfile: asObject(data.risk_profile, "risk profile"),
    normalizationVersion: stringValue(data, "normalization_version"),
    detectorRulesetVersion: stringValue(data, "detector_ruleset_version"),
    findings,
    riskContributions: objectArray(data, "risk_contributions"),
    riskExplanation: asObject(data.risk_explanation, "risk explanation"),
    policyDecision,
    timing: asObject(data.timing, "timing"),
    correlationId: stringValue(data, "correlation_id"),
    ...(typeof data.redacted_content === "string"
      ? { redactedContent: data.redacted_content }
      : {}),
    ...(responseRequestId === undefined
      ? {}
      : { requestId: responseRequestId }),
  };
  if (
    result.riskScore < 0 ||
    result.riskScore > 100 ||
    result.confidence < 0 ||
    result.confidence > 100
  ) {
    throw protocolError("Renzai returned an invalid Analyze score.");
  }
  return result;
}

export function parseChat(payload: unknown, headers: Headers): ChatCompletion {
  const data = asObject(payload, "Gateway response");
  if (!Array.isArray(data.choices) || data.choices.length !== 1) {
    throw protocolError("Renzai returned a malformed Gateway response.");
  }
  const choice = asObject(data.choices[0], "Gateway choice");
  const message = asObject(choice.message, "Gateway message");
  if (message.role !== "assistant" || typeof message.content !== "string") {
    throw protocolError("Renzai returned a malformed Gateway message.");
  }
  if (choice.finish_reason !== "stop" && choice.finish_reason !== "length") {
    throw protocolError("Renzai returned an invalid finish reason.");
  }
  const usage =
    data.usage === undefined
      ? undefined
      : asObject(data.usage, "Gateway usage");
  if (
    usage !== undefined &&
    Object.values(usage).some((value) => typeof value !== "number")
  ) {
    throw protocolError("Renzai returned invalid usage data.");
  }
  const rawInputAction = headers.get("x-renzai-input-action");
  const rawOutputAction = headers.get("x-renzai-output-action");
  const inputAction =
    rawInputAction === null
      ? null
      : enumValue({ action: rawInputAction }, "action", ACTIONS);
  const outputAction =
    rawOutputAction === null
      ? null
      : enumValue({ action: rawOutputAction }, "action", ACTIONS);
  const responseRequestId = requestId(headers);
  const inputAnalysisId = headers.get("x-renzai-input-analysis-id");
  const outputAnalysisId = headers.get("x-renzai-output-analysis-id");
  return {
    id: stringValue(data, "id"),
    created: numberValue(data, "created"),
    model: stringValue(data, "model"),
    content: message.content,
    finishReason: choice.finish_reason,
    ...(usage === undefined ? {} : { usage: usage as Record<string, number> }),
    ...(responseRequestId === undefined
      ? {}
      : { requestId: responseRequestId }),
    ...(inputAnalysisId === null ? {} : { inputAnalysisId }),
    ...(outputAnalysisId === null ? {} : { outputAnalysisId }),
    ...(inputAction === null ? {} : { inputAction }),
    ...(outputAction === null ? {} : { outputAction }),
  };
}

export function parseIncident(payload: unknown): Incident {
  const data = asObject(payload, "incident");
  return {
    incidentId: stringValue(data, "incident_id"),
    organizationId: stringValue(data, "organization_id"),
    status: enumValue(data, "status", INCIDENT_STATUSES),
    severity: enumValue(data, "severity", SEVERITIES),
    source: enumValue(data, "source", INCIDENT_SOURCES),
    title: stringValue(data, "title"),
    safeSummary: stringValue(data, "safe_summary"),
    version: numberValue(data, "version"),
    createdAt: stringValue(data, "created_at"),
    updatedAt: stringValue(data, "updated_at"),
    applicationId:
      typeof data.application_id === "string" ? data.application_id : null,
    environmentId:
      typeof data.environment_id === "string" ? data.environment_id : null,
    assigneeUserId:
      typeof data.assignee_user_id === "string" ? data.assignee_user_id : null,
    action:
      typeof data.action === "string"
        ? enumValue({ action: data.action }, "action", ACTIONS)
        : null,
    riskScore: typeof data.risk_score === "number" ? data.risk_score : null,
    category: typeof data.category === "string" ? data.category : null,
    resolvedAt: typeof data.resolved_at === "string" ? data.resolved_at : null,
    details: data,
  };
}

export function parseIncidentPage(
  payload: unknown,
  responseRequestId?: string,
): IncidentPage {
  const data = asObject(payload, "incident page");
  if (
    !Array.isArray(data.items) ||
    (data.next_cursor !== null && typeof data.next_cursor !== "string")
  ) {
    throw protocolError("Renzai returned a malformed incident page.");
  }
  return {
    items: data.items.map(parseIncident),
    nextCursor: data.next_cursor,
    limit: numberValue(data, "limit"),
    ...(responseRequestId === undefined
      ? {}
      : { requestId: responseRequestId }),
  };
}

export function parseAnalytics(
  payload: unknown,
  responseRequestId?: string,
): AnalyticsDashboard {
  const data = asObject(payload, "analytics response");
  return {
    filters: asObject(data.filters, "analytics filters"),
    summary: asObject(data.summary, "analytics summary"),
    activity: objectArray(data, "activity"),
    riskDistribution: objectArray(data, "risk_distribution"),
    threatCategories: objectArray(data, "threat_categories"),
    topDetectors: objectArray(data, "top_detectors"),
    policyActions: objectArray(data, "policy_actions"),
    applications: objectArray(data, "applications"),
    environments: objectArray(data, "environments"),
    providers: objectArray(data, "providers"),
    incidents: asObject(data.incidents, "incident analytics"),
    recentIncidents: objectArray(data, "recent_incidents"),
    queryDurationMs: numberValue(data, "query_duration_ms"),
    ...(responseRequestId === undefined
      ? {}
      : { requestId: responseRequestId }),
  };
}

export function parseAI(
  payload: unknown,
  responseRequestId?: string,
): AIIntelligenceResult {
  const data = asObject(payload, "AI intelligence response");
  return {
    requestId: stringValue(data, "request_id"),
    incidentId: stringValue(data, "incident_id"),
    taskType: enumValue(data, "task_type", AI_TASKS),
    status: enumValue(data, "status", AI_STATUSES),
    aiGenerated: trueValue(data, "ai_generated"),
    contextMode: enumValue(data, "context_mode", DISCLOSURE_MODES),
    incidentVersion: numberValue(data, "incident_version"),
    providerId: stringValue(data, "provider_id"),
    providerName: stringValue(data, "provider_name"),
    model: stringValue(data, "model"),
    promptTemplateVersion:
      typeof data.prompt_template_version === "string"
        ? data.prompt_template_version
        : null,
    inputContextVersion: stringValue(data, "input_context_version"),
    outputSchemaVersion: stringValue(data, "output_schema_version"),
    content:
      data.content === null ? null : asObject(data.content, "AI content"),
    usage:
      data.usage === null
        ? null
        : (asObject(data.usage, "AI usage") as Record<string, number | null>),
    errorCode: typeof data.error_code === "string" ? data.error_code : null,
    createdAt: stringValue(data, "created_at"),
    completedAt:
      typeof data.completed_at === "string" ? data.completed_at : null,
    ...(responseRequestId === undefined ? {} : { responseRequestId }),
  };
}
