import { Renzai } from "@renzai/sdk";

// Server route only. Never import this module into a client component or browser bundle.
export async function POST(request: Request): Promise<Response> {
  const body = (await request.json()) as { selectedText?: unknown };
  if (typeof body.selectedText !== "string") {
    return Response.json({ error: "selectedText is required" }, { status: 400 });
  }
  const client = new Renzai({
    apiKey: process.env.RENZAI_API_KEY!,
    baseUrl: process.env.RENZAI_BASE_URL ?? "http://localhost:8000",
  });
  const result = await client.analyze({ content: body.selectedText, direction: "input" });
  return Response.json({ action: result.action, requestId: result.requestId });
}
