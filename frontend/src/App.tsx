/**
 * App — root component of My Skilled Self.
 *
 * Layout:
 *   ┌─────────────────────────────┐
 *   │  Header + MarketTicker      │
 *   ├─────────────────────────────┤
 *   │  Chat messages (scrollable) │
 *   ├─────────────────────────────┤
 *   │  ChatInput + quick prompts  │
 *   └─────────────────────────────┘
 */

import React, { useEffect, useRef } from 'react';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { MarketTicker } from './components/MarketTicker';
import { SkillsBadge } from './components/SkillsBadge';
import { useAgent } from './hooks/useAgent';
import './index.css';

const WELCOME_TEXT = `👋 Welcome to **My Skilled Self** — your AI-powered trading and investing advisor.

I have two expert skills at my disposal:

📈 **Trading Advisor** — Live stock quotes, technical analysis (RSI, MACD, Bollinger Bands),
fundamental analysis, market overviews, sector rotation, and the latest news.

📊 **Chart Generator** — Interactive candlestick charts, technical multi-panel charts,
performance comparisons, sector heat maps, and volume profiles.

**Try asking:**
- *"Analyse AAPL — give me technicals and a chart"*
- *"How is the market today?"*
- *"Compare TSLA, NVDA and AMD over 6 months with a chart"*
- *"Show me sector performance"*

All analysis is for educational purposes and does not constitute financial advice.`;

export default function App() {
  const { messages, isLoading, error, sendMessage, stopStreaming, clearMessages } =
    useAgent();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="app-header-left">
          <span className="app-logo">🧠</span>
          <div>
            <h1 className="app-title">My Skilled Self</h1>
            <p className="app-subtitle">AI Trading &amp; Investing Advisor</p>
          </div>
        </div>
        <div className="app-header-right">
          <SkillsBadge />
          <button
            className="btn btn--ghost"
            onClick={clearMessages}
            title="Clear conversation"
          >
            🗑 Clear
          </button>
        </div>
      </header>

      {/* Market ticker */}
      <MarketTicker />

      {/* Chat area */}
      <main className="chat-area">
        {/* Welcome message */}
        {messages.length === 0 && (
          <div className="welcome-message">
            <div className="message message--assistant">
              <div className="message-avatar">🤖</div>
              <div className="message-bubble">
                <div className="message-text">
                  {WELCOME_TEXT.split('\n').map((line, i) => {
                    if (!line.trim()) return <br key={i} />;
                    // Render bold markdown manually for the welcome message
                    const parts = line.split(/(\*\*[^*]+\*\*)/g);
                    return (
                      <p key={i}>
                        {parts.map((p, j) =>
                          p.startsWith('**') && p.endsWith('**') ? (
                            <strong key={j}>{p.slice(2, -2)}</strong>
                          ) : (
                            <span key={j}>{p}</span>
                          ),
                        )}
                      </p>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Message history */}
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {/* Error banner */}
        {error && (
          <div className="error-banner">
            ⚠️ {error}
            <button className="error-dismiss" onClick={() => {}}>
              ✕
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* Input */}
      <footer className="app-footer">
        <ChatInput
          onSend={sendMessage}
          onStop={stopStreaming}
          isLoading={isLoading}
        />
      </footer>
    </div>
  );
}
