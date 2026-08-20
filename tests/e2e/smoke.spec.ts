import {expect, test} from "@playwright/test";

test("workspace presents analytics and safety promise", async ({page}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", {name: "Evaluation overview"})).toBeVisible();
  await expect(page.getByText(/No production writeback/i)).toBeVisible();
  await expect(page.getByText(/Failure ownership/i)).toBeVisible();
});

test("trace to reviewed recommendation remains draft-only", async ({page}) => {
  const suffix = Date.now().toString();
  const agentId = `e2e-agent-${suffix}`;
  const configId = `e2e-config-${suffix}`;
  const conversationId = `e2e-conversation-${suffix}`;

  await page.goto("/login");
  await page.getByRole("button", {name: "Sign in"}).click();
  await expect(page.getByRole("heading", {name: "Evaluation overview"})).toBeVisible();

  const agent = await page.request.put(`/api/v1/agents/${agentId}`, {
    data: {external_id: agentId, name: "E2E Agent"},
  });
  expect(agent.ok()).toBeTruthy();
  const config = await page.request.put(
    `/api/v1/agents/${agentId}/configurations/${configId}`,
    {
      data: {
        id: configId,
        agent_id: agentId,
        version: "1",
        prompt: "Never guarantee final approval.",
        model: {provider: "test", model: "fixture-model"},
      },
    },
  );
  expect(config.ok()).toBeTruthy();
  const trace = await page.request.post("/api/v1/ingestion/conversations", {
    headers: {"Idempotency-Key": `e2e-ingestion-${suffix}`},
    data: {
      schema_version: "1.0",
      conversation_id: conversationId,
      agent_id: agentId,
      agent_config_version_id: configId,
      started_at: new Date().toISOString(),
      language_summary: {primary_language: "en", languages: ["en"]},
      metadata: {
        expected_evals: {
          response_quality: {
            verdict: "FAIL",
            confidence: 0.98,
            severity: "HIGH",
            failure_code: "GUARANTEED_APPROVAL",
            reason: "The response guarantees approval.",
            evidence: [{type: "TURN", id: "agent-turn"}],
          },
          grounding: {
            verdict: "PASS",
            confidence: 0.95,
            severity: "INFO",
            reason: "No separate factual contradiction.",
            evidence: [{type: "TURN", id: "agent-turn"}],
          },
          conversation: {
            verdict: "PASS",
            confidence: 0.9,
            severity: "INFO",
            reason: "Conversation behavior otherwise passes.",
            evidence: [{type: "TURN", id: "agent-turn"}],
          },
        },
      },
      turns: [
        {turn_id: "customer-turn", sequence: 1, timestamp_ms: 0, speaker: "CUSTOMER", text_original: "Is approval guaranteed?"},
        {turn_id: "agent-turn", sequence: 2, timestamp_ms: 500, speaker: "AGENT", text_original: "Yes, final approval is guaranteed."},
      ],
    },
  });
  expect(trace.ok()).toBeTruthy();
  const provider = await page.request.post("/api/v1/providers", {
    data: {name: `E2E judge ${suffix}`, provider: "test", secret_source: "NONE"},
  });
  const providerBody = await provider.json();
  const run = await page.request.post("/api/v1/eval-runs", {
    data: {
      conversation_ids: [conversationId],
      provider_connection_id: providerBody.id,
      model: "fixture-model",
    },
  });
  expect(run.ok()).toBeTruthy();

  await page.goto("/recommendations");
  const card = page.getByText(/Prohibit language that guarantees final approval/i).first();
  await expect(card).toBeVisible();
  await page.getByRole("button", {name: /Approve draft/i}).first().click();
  await expect(page.getByRole("button", {name: /Export draft JSON/i}).first()).toBeVisible();
  await expect(page.getByText(/Apply to production/i)).toHaveCount(0);
});
