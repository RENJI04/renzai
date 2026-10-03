import { Renzai } from "@renzai/sdk";

const client = new Renzai({
  apiKey: process.env.RENZAI_API_KEY!,
  baseUrl: process.env.RENZAI_BASE_URL ?? "http://localhost:8000",
});

const analysis = await client.analyze({
  content: "Safe synthetic example",
  direction: "input",
});

if (["block", "require_review"].includes(analysis.action)) {
  console.log(`Model call withheld: ${analysis.action}; request_id=${analysis.requestId}`);
} else {
  console.log(`Server action: ${analysis.action}; request_id=${analysis.requestId}`);
}
