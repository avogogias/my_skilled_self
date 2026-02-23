/**
 * MarketTicker — live scrolling ticker bar showing major indices.
 */

import React, { useEffect, useState } from 'react';
import { getMarketOverview } from '@/services/api';
import type { MarketOverview } from '@/types';

export const MarketTicker: React.FC = () => {
  const [data, setData] = useState<MarketOverview | null>(null);

  useEffect(() => {
    const fetch = () =>
      getMarketOverview()
        .then(setData)
        .catch(() => {});
    fetch();
    const id = setInterval(fetch, 60_000); // Refresh every minute
    return () => clearInterval(id);
  }, []);

  if (!data) return <div className="ticker-bar ticker-bar--loading">Loading market data…</div>;

  const entries = Object.entries(data.indices);

  return (
    <div className="ticker-bar" aria-label="Market indices">
      <div className="ticker-track">
        {[...entries, ...entries].map(([name, q], i) => (
          <span key={`${name}-${i}`} className="ticker-item">
            <span className="ticker-name">{name}</span>
            <span className="ticker-price">{q.price.toLocaleString()}</span>
            <span
              className={`ticker-change ${
                q.change_pct >= 0 ? 'ticker-change--up' : 'ticker-change--down'
              }`}
            >
              {q.change_pct >= 0 ? '▲' : '▼'} {Math.abs(q.change_pct).toFixed(2)}%
            </span>
          </span>
        ))}
      </div>
    </div>
  );
};
