export type Direction = "input" | "output";
export type Severity = "low" | "medium" | "high" | "critical";
export type Category =
  | "prompt_injection"
  | "instruction_override"
  | "system_prompt_extraction"
  | "jailbreak"
  | "role_manipulation"
  | "encoded_obfuscated"
  | "secret_exposure"
  | "pii_exposure"
  | "suspicious_url"
  | "tool_manipulation_indicator"
  | "data_exfiltration_indicator";
export type Action = "allow" | "flag" | "block" | "redact" | "require_review";
export type IncidentStatus =
  "open" | "investigating" | "resolved" | "ignored" | "false_positive";
export type IncidentSeverity = Severity;
export type AITaskType =
  | "incident_summary"
  | "attack_explanation"
  | "mitigation_suggestion"
  | "policy_suggestion";
export type DisclosureMode = "metadata_only" | "redacted" | "full";
export type AIStatus = "pending" | "running" | "completed" | "failed";
export type JsonObject = Record<string, unknown>;

export type RetryPolicy = {
  maxAttempts?: number;
  initialBackoffMs?: number;
  maximumBackoffMs?: number;
};

export type RequestOptions = { signal?: AbortSignal };

export type AnalyzeInput = {
  content: string;
  direction: Direction;
  correlationId?: string;
  metadata?: Record<string, string>;
};

export type Finding = {
  findingId: string;
  detectorId: string;
  detectorVersion: string;
  rulesetVersion: string;
  category: Category;
  direction: Direction;
  severity: Severity;
  confidence: number;
  evidence: JsonObject;
  safeExplanation: string;
  metadata: Record<string, string>;
};

export type PolicyDecision = {
  policyDecisionId: string;
  rationaleCode: string;
  redactionTargets: string[];
  policyMatch: JsonObject | null;
  evaluatedPolicyVersions: JsonObject[];
  scopeWinners: JsonObject[];
};

export type AnalyzeResult = {
  analysisId: string;
  eventId: string;
  timestamp: string;
  direction: Direction;
  source: string;
  safe: boolean;
  noDetectedThreat: boolean;
  action: Action;
  riskScore: number;
  severity: Severity;
  confidence: number;
  riskProfile: JsonObject;
  normalizationVersion: string;
  detectorRulesetVersion: string;
  findings: Finding[];
  riskContributions: JsonObject[];
  riskExplanation: JsonObject;
  policyDecision: PolicyDecision;
  timing: JsonObject;
  correlationId: string;
  redactedContent?: string;
  requestId?: string;
};

export type RiskResult = Pick<
  AnalyzeResult,
  | "riskScore"
  | "severity"
  | "confidence"
  | "riskProfile"
  | "riskContributions"
  | "riskExplanation"
>;

export type ChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};
export type ChatCompletionInput = {
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  topP?: number;
  maxTokens?: number;
  stop?: string | string[];
  presencePenalty?: number;
  frequencyPenalty?: number;
  seed?: number;
};
export type ChatCompletion = {
  id: string;
  created: number;
  model: string;
  content: string;
  finishReason: "stop" | "length";
  usage?: Record<string, number>;
  requestId?: string;
  inputAnalysisId?: string;
  outputAnalysisId?: string;
  inputAction?: Action;
  outputAction?: Action;
};

export type Incident = {
  incidentId: string;
  organizationId: string;
  status: IncidentStatus;
  severity: IncidentSeverity;
  source: "manual" | "gateway" | "analyze" | "playground";
  title: string;
  safeSummary: string;
  version: number;
  createdAt: string;
  updatedAt: string;
  applicationId?: string | null;
  environmentId?: string | null;
  assigneeUserId?: string | null;
  action?: Action | null;
  riskScore?: number | null;
  category?: string | null;
  resolvedAt?: string | null;
  details: JsonObject;
};

export type IncidentFilters = {
  status?: IncidentStatus[];
  severity?: IncidentSeverity[];
  applicationId?: string;
  environmentId?: string;
  assigneeUserId?: string;
  unassigned?: boolean;
  source?: "manual" | "gateway" | "analyze" | "playground";
  action?: Action;
  category?: string;
  from?: string;
  to?: string;
  search?: string;
};

export type IncidentPage = {
  items: Incident[];
  nextCursor: string | null;
  limit: number;
  requestId?: string;
};

export type AnalyticsDashboard = {
  filters: JsonObject;
  summary: JsonObject;
  activity: JsonObject[];
  riskDistribution: JsonObject[];
  threatCategories: JsonObject[];
  topDetectors: JsonObject[];
  policyActions: JsonObject[];
  applications: JsonObject[];
  environments: JsonObject[];
  providers: JsonObject[];
  incidents: JsonObject;
  recentIncidents: JsonObject[];
  queryDurationMs: number;
  requestId?: string;
};

export type AIIntelligenceResult = {
  requestId: string;
  incidentId: string;
  taskType: AITaskType;
  status: AIStatus;
  aiGenerated: true;
  contextMode: DisclosureMode;
  incidentVersion: number;
  providerId: string;
  providerName: string;
  model: string;
  promptTemplateVersion: string | null;
  inputContextVersion: string;
  outputSchemaVersion: string;
  content: JsonObject | null;
  usage: Record<string, number | null> | null;
  errorCode: string | null;
  createdAt: string;
  completedAt: string | null;
  responseRequestId?: string;
};
