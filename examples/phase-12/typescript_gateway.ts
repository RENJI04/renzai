import { Renzai } from "@renzai/sdk";

const client = new Renzai({
  apiKey: process.env.RENZAI_API_KEY!,
  baseUrl: process.env.RENZAI_BASE_URL ?? "http://localhost:8000",
});

const completion = await client.gateway.create({
  model: "configured-model",
  messages: [{ role: "user", content: "Safe synthetic example" }],
});

console.log(completion.content);
