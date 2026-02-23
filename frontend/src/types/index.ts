/** Shared TypeScript types for the My Skilled Self frontend. */

// ── Agent API ──────────────────────────────────────────────────────────────

export type SSEEventType =
  | 'text_chunk'
  | 'tool_call'
  | 'tool_result'
  | 'chart'
  | 'done'
  | 'error';

export interface SSEEvent {
  type: SSEEventType;
  // text_chunk
  content?: string;
  // tool_call
  name?: string;
  args?: Record<string, unknown>;
  // tool_result
  result?: Record<string, unknown>;
  // chart
  chart_type?: string;
  ticker?: string;
  spec?: PlotlySpec;
  // error
  message?: string;
}

export interface ChatRequest {
  message: string;
  session_id: string;
  user_id?: string;
}

// ── Messages ───────────────────────────────────────────────────────────────

export type MessageRole = 'user' | 'assistant';

export type MessagePart =
  | { kind: 'text'; content: string }
  | { kind: 'chart'; chart_type: string; ticker?: string; spec: PlotlySpec }
  | { kind: 'tool_call'; name: string; args: Record<string, unknown> };

export interface Message {
  id: string;
  role: MessageRole;
  parts: MessagePart[];
  timestamp: Date;
  isStreaming?: boolean;
}

// ── Plotly ─────────────────────────────────────────────────────────────────

export interface PlotlySpec {
  data: Record<string, unknown>[];
  layout: Record<string, unknown>;
  config?: Record<string, unknown>;
  error?: string;
}

// ── Market ─────────────────────────────────────────────────────────────────

export interface IndexQuote {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
}

export interface MarketOverview {
  indices: Record<string, IndexQuote>;
  timestamp: string;
}

export interface SectorData {
  etf: string;
  price: number;
  change_pct_1d: number;
}

export interface SectorPerformance {
  sectors: Record<string, SectorData>;
  timestamp: string;
}

// ── Skills ─────────────────────────────────────────────────────────────────

export interface SkillInfo {
  name: string;
  description: string;
  version: string;
  tags: string[];
  icon: string;
  tools: string[];
}
