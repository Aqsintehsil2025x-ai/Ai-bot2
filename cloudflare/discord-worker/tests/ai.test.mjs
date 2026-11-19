import test from "node:test";
import assert from "node:assert/strict";
import { generateAI, runDeferredAI } from "../src/ai.ts";

const env = {
  GEMINI_API_KEY: { get: async () => "test-gemini-key" },
  NVIDIA_API_KEY: { get: async () => "test-nvidia-key" },
  DISCORD_TOKEN: { get: async () => "test-discord-token" },
};

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("Gemini success returns the actual provider and model", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (url, init) => {
    assert.match(String(url), /models\/gemini-3\.8-flash:generateContent$/);
    assert.equal(new Headers(init.headers).get("x-goog-api-key"), "test-gemini-key");
    assert.equal(String(url).includes("test-gemini-key"), false);
    return jsonResponse({ candidates: [{ content: { parts: [{ text: "Merhaba!" }] } }] });
  };

  const result = await generateAI(env, "gemini", "Merhaba");
  assert.equal(result.text, "Merhaba!");
  assert.equal(result.provider, "gemini");
  assert.equal(result.model, "gemini-3.8-flash");
  assert.equal(result.fallback, false);
});

test("NVIDIA 410 fails over to Gemini and reports the fallback", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  const calls = [];
  globalThis.fetch = async (url) => {
    calls.push(String(url));
    if (String(url).includes("integrate.api.nvidia.com")) {
      return jsonResponse({ detail: "inference unavailable" }, 410);
    }
    return jsonResponse({ candidates: [{ content: { parts: [{ text: "Gemini ehtiyat cavabı" }] } }] });
  };

  const result = await generateAI(env, "nvidia", "Test");
  assert.equal(result.provider, "gemini");
  assert.equal(result.fallback, true);
  assert.equal(result.text, "Gemini ehtiyat cavabı");
  assert.equal(calls.length, 2);
});

test("Gemini overload retries once, then uses NVIDIA", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  let geminiCalls = 0;
  globalThis.fetch = async (url) => {
    if (String(url).includes("generativelanguage.googleapis.com")) {
      geminiCalls++;
      return jsonResponse({ error: { message: "busy" } }, 429);
    }
    return jsonResponse({ choices: [{ message: { content: "NVIDIA ehtiyat cavabı" } }] });
  };

  const result = await generateAI(env, "gemini", "Test");
  assert.equal(geminiCalls, 4);
  assert.equal(result.provider, "nvidia");
  assert.equal(result.fallback, true);
  assert.equal(result.text, "NVIDIA ehtiyat cavabı");
});

test("both provider failures are surfaced without exposing API keys", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (url) => String(url).includes("integrate.api.nvidia.com")
    ? jsonResponse({ detail: "gone" }, 410)
    : jsonResponse({ error: { message: "busy" } }, 503);

  await assert.rejects(
    generateAI(env, "nvidia", "Test"),
    (error) => {
      assert.match(error.message, /NVIDIA HTTP 410/);
      assert.match(error.message, /GEMINI API HTTP 503/);
      assert.equal(error.message.includes("test-nvidia-key"), false);
      assert.equal(error.message.includes("test-gemini-key"), false);
      return true;
    },
  );
});

test("deferred AI edits the original Discord interaction", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  let edited = null;
  globalThis.fetch = async (url, init) => {
    assert.match(String(url), /webhooks\/app-id\/interaction-token\/messages\/@original$/);
    edited = JSON.parse(init.body);
    return new Response(null, { status: 204 });
  };

  await runDeferredAI(
    { application_id: "app-id", token: "interaction-token" },
    env,
    "gemini",
    "Test",
  );
  assert.equal(typeof edited?.content, "string");
  assert.match(edited.content, /Merhaba!/);
});
