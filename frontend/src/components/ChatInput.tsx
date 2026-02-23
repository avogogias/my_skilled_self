/**
 * ChatInput — textarea with send/stop controls and quick-prompt chips.
 */

import React, { KeyboardEvent, useRef, useState } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop: () => void;
  isLoading: boolean;
  disabled?: boolean;
}

const QUICK_PROMPTS = [
  'What is the market doing today?',
  'Analyse AAPL with technical indicators',
  'Show me a candlestick chart for TSLA',
  'Compare AAPL, MSFT, GOOGL over 1 year',
  'Show sector performance chart',
  'What are the fundamentals of NVDA?',
];

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  onStop,
  isLoading,
  disabled = false,
}) => {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <div className="chat-input-wrapper">
      {/* Quick prompt chips */}
      <div className="quick-prompts">
        {QUICK_PROMPTS.map((p) => (
          <button
            key={p}
            className="quick-prompt-chip"
            onClick={() => {
              setValue(p);
              textareaRef.current?.focus();
            }}
            disabled={isLoading}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="chat-input-row">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Ask about markets, stocks, charts… (Enter to send, Shift+Enter for newline)"
          rows={1}
          disabled={disabled || isLoading}
        />
        {isLoading ? (
          <button className="btn btn--stop" onClick={onStop} title="Stop">
            ⏹ Stop
          </button>
        ) : (
          <button
            className="btn btn--send"
            onClick={handleSend}
            disabled={!value.trim() || disabled}
            title="Send (Enter)"
          >
            ➤ Send
          </button>
        )}
      </div>
      <p className="chat-input-hint">
        Enter to send · Shift+Enter for newline · Powered by Google Gemini + ADK
      </p>
    </div>
  );
};
