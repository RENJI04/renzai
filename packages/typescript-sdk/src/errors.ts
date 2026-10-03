import type { JsonObject } from "./types.js";

export class RenzaiError extends Error {
  readonly code: string;
  readonly requestId: string | undefined;
  readonly details: JsonObject | undefined;
  readonly statusCode: number | undefined;

  constructor(
    message: string,
    options: {
      code: string;
      requestId?: string;
      details?: JsonObject;
      statusCode?: number;
    },
    errorOptions?: ErrorOptions,
  ) {
    super(message, errorOptions);
    this.name = new.target.name;
    this.code = options.code;
    this.requestId = options.requestId;
    this.details = options.details;
    this.statusCode = options.statusCode;
  }
}

export class ValidationError extends RenzaiError {}
export class AuthenticationError extends RenzaiError {}
export class AuthorizationError extends RenzaiError {}
export class NotFoundError extends RenzaiError {}
export class ConflictError extends RenzaiError {}
export class RateLimitError extends RenzaiError {}
export class PolicyBlockError extends RenzaiError {}
export class ReviewRequiredError extends RenzaiError {}
export class ProviderError extends RenzaiError {}
export class InspectionError extends RenzaiError {}
export class ConfigurationError extends RenzaiError {}
export class RenzaiTimeoutError extends RenzaiError {}
export class RenzaiConnectionError extends RenzaiError {}
export class RenzaiProtocolError extends RenzaiError {}

export const errorTypes: Record<string, typeof RenzaiError> = {
  validation: ValidationError,
  authentication: AuthenticationError,
  authorization: AuthorizationError,
  not_found_or_hidden: NotFoundError,
  conflict: ConflictError,
  invalid_transition: ConflictError,
  rate_limit: RateLimitError,
  policy_block: PolicyBlockError,
  review_required: ReviewRequiredError,
  provider_timeout: RenzaiTimeoutError,
  provider_error: ProviderError,
  inspection_failure: InspectionError,
  configuration_error: ConfigurationError,
};
