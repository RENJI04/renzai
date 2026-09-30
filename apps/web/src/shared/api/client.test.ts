import { describe, expect, it } from "vitest";
import { RenzaiApiError } from "./client";

describe("RenzaiApiError", () => {
  it("preserves stable error details without changing the envelope", () => {
    const error = new RenzaiApiError({
      error: { code: "validation", message: "The request is invalid.", request_id: "req-1" },
    });
    expect(error.code).toBe("validation");
    expect(error.requestId).toBe("req-1");
  });
});
