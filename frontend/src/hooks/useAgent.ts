/**
 * useAgent — React hook for interacting with the My Skilled Self agent.
 *
 * Manages:
 *   - Message history (user + assistant turns)
 *   - Session ID persistence (survives hot-reloads, not page refreshes by design)
 *   - Streaming SSE parsing into structured MessagePart objects
 *   - Loading / error state
 */

import { useCallback, useRef, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { streamChat } from '@/services/api';
import type { Message, MessagePart, SSEEvent } from '@/types';

// Simple UUID v4 polyfill if uuid package isn't available
function makeId(): string {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function useAgent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sessionIdRef = useRef<string>(makeId());
  const abortRef = useRef<AbortController | null>(null);
  const assistantIdRef = useRef<string | null>(null);

  const sendMessage = useCallback(async (userText: string) => {
    if (!userText.trim() || isLoading) return;

    setError(null);

    // Add user message
    const userMsg: Message = {
      id: makeId(),
      role: 'user',
      parts: [{ kind: 'text', content: userText }],
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Create streaming assistant message placeholder
    const assistantId = makeId();
    assistantIdRef.current = assistantId;
    const assistantMsg: Message = {
      id: assistantId,
      role: 'assistant',
      parts: [],
      timestamp: new Date(),
      isStreaming: true,
    };
    setMessages((prev) => [...prev, assistantMsg]);

    setIsLoading(true);
    abortRef.current = new AbortController();

    try {
      // Accumulate text chunks into a single part
      let currentText = '';

      const handleEvent = (event: SSEEvent) => {
        if (event.type === 'text_chunk' && event.content) {
          currentText += event.content;
          // Capture text value now — React may batch and delay state updaters,
          // so we must not close over the mutable `currentText` variable directly.
          const snapshot = currentText;
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              const textPart: MessagePart = { kind: 'text', content: snapshot };
              // Replace existing text part or add new one
              const nonText = m.parts.filter((p) => p.kind !== 'text');
              return { ...m, parts: [textPart, ...nonText] };
            }),
          );
        } else if (event.type === 'chart' && event.spec && !event.spec.error) {
          const chartPart: MessagePart = {
            kind: 'chart',
            chart_type: event.chart_type ?? 'unknown',
            ticker: event.ticker,
            spec: event.spec,
          };
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, parts: [...m.parts, chartPart] } : m,
            ),
          );
        } else if (event.type === 'tool_call' && event.name) {
          const toolPart: MessagePart = {
            kind: 'tool_call',
            name: event.name,
            args: event.args ?? {},
          };
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, parts: [...m.parts, toolPart] } : m,
            ),
          );
        } else if (event.type === 'done') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, isStreaming: false } : m,
            ),
          );
          setIsLoading(false);
        } else if (event.type === 'error') {
          setError(event.message ?? 'Unknown error from agent.');
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, isStreaming: false } : m,
            ),
          );
          setIsLoading(false);
        }
      };

      await streamChat(
        {
          message: userText,
          session_id: sessionIdRef.current,
          user_id: 'web_user',
        },
        handleEvent,
        abortRef.current.signal,
      );
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      const msg = err instanceof Error ? err.message : 'Connection failed.';
      setError(msg);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, isStreaming: false } : m,
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
    setMessages((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m)),
    );
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    sessionIdRef.current = makeId(); // New session
  }, []);

  return {
    messages,
    isLoading,
    error,
    sessionId: sessionIdRef.current,
    sendMessage,
    stopStreaming,
    clearMessages,
  };
}
