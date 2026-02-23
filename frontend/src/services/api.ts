/**
 * API service layer — wraps all calls to the FastAPI agent backend.
 *
 * Streaming is handled via the native EventSource-less fetch + ReadableStream
 * approach so we get SSE without the EventSource URL-limitation restriction.
 */

import type {
  ChatRequest,
  MarketOverview,
  SectorPerformance,
  SkillInfo,
  SSEEvent,
} from '@/types';

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api';

// ── Helpers ────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ── Health ─────────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<{ status: string; model: string }> {
  return apiFetch('/health');
}

// ── Skills ─────────────────────────────────────────────────────────────────

export async function getSkills(): Promise<{ skills: SkillInfo[] }> {
  return apiFetch('/skills');
}

// ── Market ─────────────────────────────────────────────────────────────────

export async function getMarketOverview(): Promise<MarketOverview> {
  return apiFetch('/market/overview');
}

export async function getSectorPerformance(): Promise<SectorPerformance> {
  return apiFetch('/market/sectors');
}

// ── Streaming Chat ─────────────────────────────────────────────────────────

/**
 * Stream agent responses from the /chat/stream endpoint.
 *
 * @param req     Chat request payload
 * @param onEvent Callback invoked for each parsed SSE event
 * @param signal  Optional AbortSignal to cancel the stream
 */
export async function streamChat(
  req: ChatRequest,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Stream error ${res.status}: ${detail}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('data: ')) {
        const jsonStr = trimmed.slice(6);
        try {
          const event: SSEEvent = JSON.parse(jsonStr);
          onEvent(event);
        } catch {
          // Ignore malformed lines
        }
      }
    }
  }
}

// ── Non-streaming Chat ─────────────────────────────────────────────────────

export async function sendChat(req: ChatRequest) {
  return apiFetch<{
    text: string;
    charts: SSEEvent[];
    tool_calls: SSEEvent[];
    session_id: string;
  }>('/chat', { method: 'POST', body: JSON.stringify(req) });
}
