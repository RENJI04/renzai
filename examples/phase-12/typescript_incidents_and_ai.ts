import { RenzaiSession } from "@renzai/sdk";

const client = new RenzaiSession({
  sessionToken: process.env.RENZAI_SESSION_TOKEN!,
  csrfToken: process.env.RENZAI_CSRF_TOKEN!,
  cookieName: "renzai_session",
  baseUrl: process.env.RENZAI_BASE_URL ?? "http://localhost:8000",
});

const organizationId = process.env.RENZAI_ORGANIZATION_ID!;
const page = await client.listIncidents(organizationId, { limit: 10 });
for (const incident of page.items) console.log(incident.incidentId, incident.status);

if (page.items[0] !== undefined) {
  await client.requestAI(organizationId, page.items[0].incidentId, {
    taskType: "incident_summary",
    idempotencyKey: "replace-with-stable-operation-key",
  });
}
