/**
 * ChatMessage — renders a single message turn (user or assistant).
 *
 * Assistant messages can contain interleaved text and charts.
 * Tool call indicators are shown as subtle badges.
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChartDisplay } from './ChartDisplay';
import type { Message, MessagePart } from '@/types';

interface ChatMessageProps {
  message: Message;
}

const CHART_TYPE_LABELS: Record<string, string> = {
  candlestick: '🕯️ Candlestick Chart',
  technical: '📊 Technical Analysis',
  line: '📈 Price Chart',
  area: '📈 Price Area Chart',
  comparison: '⚖️ Comparison Chart',
  sector: '🏭 Sector Performance',
  volume_profile: '📦 Volume Profile',
};

const ToolCallBadge: React.FC<{ name: string; args: Record<string, unknown> }> = ({ name, args }) => {
  const argStr = Object.entries(args)
    .map(([k, v]) => `${k}: ${v}`)
    .join(', ');
  return (
    <div className="tool-call-badge">
      <span className="tool-call-icon">⚙️</span>
      <span className="tool-call-name">{name.replace('tool_', '')}</span>
      {argStr && <span className="tool-call-args">({argStr})</span>}
    </div>
  );
};

const MessageParts: React.FC<{ parts: MessagePart[]; isStreaming?: boolean }> = ({
  parts,
  isStreaming,
}) => {
  // Separate text (first) from others for clean ordering
  const textPart = parts.find((p) => p.kind === 'text');
  const nonTextParts = parts.filter((p) => p.kind !== 'text');

  return (
    <div className="message-parts">
      {textPart && textPart.kind === 'text' && (
        <div className="message-text">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {textPart.content}
          </ReactMarkdown>
          {isStreaming && <span className="streaming-cursor">▌</span>}
        </div>
      )}
      {nonTextParts.map((part, idx) => {
        if (part.kind === 'chart') {
          const label =
            CHART_TYPE_LABELS[part.chart_type] ??
            `📊 ${part.chart_type} Chart`;
          const title = part.ticker ? `${label} — ${part.ticker}` : label;
          return (
            <ChartDisplay
              key={idx}
              spec={part.spec}
              title={title}
              className="message-chart"
            />
          );
        }
        if (part.kind === 'tool_call') {
          return (
            <ToolCallBadge key={idx} name={part.name} args={part.args} />
          );
        }
        return null;
      })}
    </div>
  );
};

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  if (message.parts.length === 0) {
    return isUser ? null : (
      <div className={`message message--assistant`}>
        <div className="message-avatar">🤖</div>
        <div className="message-bubble">
          <span className="streaming-cursor">▌</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`message message--${message.role}`}>
      <div className="message-avatar">{isUser ? '👤' : '🤖'}</div>
      <div className="message-bubble">
        <MessageParts parts={message.parts} isStreaming={message.isStreaming} />
        <time className="message-time">
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </time>
      </div>
    </div>
  );
};
