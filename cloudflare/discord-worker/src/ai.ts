export type AIProvider = "gemini" | "nvidia";

export interface AIEnvironment {
  GEMINI_API_KEY: { get(): Promise<string> };
  NVIDIA_API_KEY: { get(): Promise<string> };
  DISCORD_TOKEN: { get(): Promise<string> };
}

export interface AIInteraction {
  application_id?: string;
  token?: string;
}

export interface AIResult {
  text: string;
  provider: AIProvider;
  model: string;
  fallback: boolean;
}

export class AIProviderError extends Error {
  readonly provider: AIProvider;
  readonly model: string;
  readonly status: number | null;
  readonly retryable: boolean;

  constructor(provider: AIProvider, model: string, message: string, status: number | null = null, retryable = false) {
    super(message);
    this.name = "AIProviderError";
    this.provider = provider;
    this.model = model;
    this.status = status;
    this.retryable = retryable;
  }
}

const DEFAULT_MODELS: Record<AIProvider, string[]> = {
  gemini: ["gemini-3.8-flash", "gemini-3.5-flash-lite"],
  nvidia: ["nvidia/llama-3.3-nemotron-super-49b-v1.5"],
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function safeErrorMessage(value: unknown): string {
  if (value instanceof Error) return value.message;
  return typeof value === "string" ? value : "Unknown provider error";
}

async function parseResponse(response: Response): Promise<any> {
  const raw = await response.text();
  if (!raw) return {};
  try { return JSON.parse(raw); }
  catch { return { message: raw.slice(0, 500) }; }
}

function providerMessage(provider: AIProvider, status: number, detail: string): string {
  if (provider === "nvidia" && status === 410) {
    return "NVIDIA HTTP 410: hosted inference access is unavailable for this account or endpoint. Check NVIDIA account/API access; changing model names will not fix an account-level 410.";
  }
  if (status === 401 || status === 403) return provider.toUpperCase() + " API key was rejected (HTTP " + status + "). Check the secret binding.";
  if (status === 404) return provider.toUpperCase() + " model or endpoint was not found (HTTP 404).";
  if (status === 429) return provider.toUpperCase() + " rate limit or temporary capacity limit reached (HTTP 429).";
  return provider.toUpperCase() + " API HTTP " + status + (detail ? ": " + detail : "");
}

async function callGemini(apiKey: string, model: string, prompt: string): Promise<string> {
  const url = "https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent";
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": apiKey },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: { maxOutputTokens: 1200, temperature: 0.7 },
      }),
      signal: AbortSignal.timeout(25000),
    });
  } catch (error) {
    throw new AIProviderError("gemini", model, "Gemini network/timeout error: " + safeErrorMessage(error), null, true);
  }
  const data = await parseResponse(response);
  if (!response.ok) {
    const detail = data.error?.message || data.message || "";
    throw new AIProviderError("gemini", model, providerMessage("gemini", response.status, detail), response.status, [408, 429, 500, 502, 503, 504].includes(response.status));
  }
  const answer = data.candidates?.[0]?.content?.parts?.map((part: any) => String(part.text || "")).join("").trim();
  if (!answer) throw new AIProviderError("gemini", model, "Gemini returned an empty response.");
  return answer;
}

async function callNvidia(apiKey: string, model: string, prompt: string): Promise<string> {
  let response: Response;
  try {
    response = await fetch("https://integrate.api.nvidia.com/v1/chat/completions", {
      method: "POST",
      headers: { authorization: "Bearer " + apiKey, "content-type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: prompt }],
        max_tokens: 1200,
        temperature: 0.7,
        stream: false,
      }),
      signal: AbortSignal.timeout(25000),
    });
  } catch (error) {
    throw new AIProviderError("nvidia", model, "NVIDIA network/timeout error: " + safeErrorMessage(error), null, true);
  }
  const data = await parseResponse(response);
  if (!response.ok) {
    const detail = data.detail || data.title || data.error?.message || data.message || "";
    throw new AIProviderError("nvidia", model, providerMessage("nvidia", response.status, detail), response.status, [408, 429, 500, 502, 503, 504].includes(response.status));
  }
  const answer = data.choices?.[0]?.message?.content;
  const text = typeof answer === "string" ? answer.trim() : "";
  if (!text) throw new AIProviderError("nvidia", model, "NVIDIA returned an empty response.");
  return text;
}

async function callModel(env: AIEnvironment, provider: AIProvider, model: string, prompt: string): Promise<string> {
  const key = provider === "gemini" ? await env.GEMINI_API_KEY.get() : await env.NVIDIA_API_KEY.get();
  return provider === "gemini" ? callGemini(key, model, prompt) : callNvidia(key, model, prompt);
}

async function runProvider(env: AIEnvironment, provider: AIProvider, prompt: string, requestedModel?: string): Promise<{ text: string; model: string }> {
  let lastError: unknown = null;
  const models = requestedModel && requestedModel.trim() ? [requestedModel.trim(), ...DEFAULT_MODELS[provider].filter((item) => item !== requestedModel.trim())] : DEFAULT_MODELS[provider];
  for (const model of models) {
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        return { text: await callModel(env, provider, model, prompt), model };
      } catch (error) {
        lastError = error;
        const retryable = error instanceof AIProviderError && error.retryable;
        if (!retryable || attempt === 1) break;
        await sleep(700 * (attempt + 1));
      }
    }
    // A retired model (404/410) should not be retried; continue to the next known model.
  }
  throw lastError instanceof Error ? lastError : new Error(safeErrorMessage(lastError));
}

/**
 * Calls the selected provider and transparently falls back to the other configured provider.
 * The response reports which provider actually produced the answer.
 */
export async function generateAI(env: AIEnvironment, preferred: AIProvider, prompt: string, requestedModel?: string): Promise<AIResult> {
  if (!prompt.trim() || prompt.length > 3500) throw new Error("Prompt must contain 1–3500 characters.");
  try {
    const result = await runProvider(env, preferred, prompt, requestedModel);
    return { ...result, provider: preferred, fallback: false };
  } catch (primaryError) {
    const alternate: AIProvider = preferred === "gemini" ? "nvidia" : "gemini";
    try {
      const result = await runProvider(env, alternate, prompt);
      return {
        ...result,
        provider: alternate,
        fallback: true,
      };
    } catch (fallbackError) {
      throw new Error(
        "Primary " + preferred.toUpperCase() + " failed: " + safeErrorMessage(primaryError) +
        " | Fallback " + alternate.toUpperCase() + " failed: " + safeErrorMessage(fallbackError),
      );
    }
  }
}

export async function runDeferredAI(
  interaction: AIInteraction,
  env: AIEnvironment,
  preferred: AIProvider,
  prompt: string,
  requestedModel?: string,
): Promise<void> {
  if (!interaction.application_id || !interaction.token) return;
  let content: string;
  try {
    const result = await generateAI(env, preferred, prompt, requestedModel);
    content = (result.fallback ? "↪ " + result.provider.toUpperCase() + " yedek sağlayıcı olarak kullanıldı.\n\n" : "") + result.text;
  } catch (error) {
    content = "AI sağlayıcı hatası: " + safeErrorMessage(error);
  }
  const url = "https://discord.com/api/v10/webhooks/" + interaction.application_id + "/" + interaction.token + "/messages/@original";
  const response = await fetch(url, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ content: content.slice(0, 1900), allowed_mentions: { parse: [] } }),
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) {
    console.error("Could not edit deferred AI interaction; Discord HTTP", response.status);
  }
}
