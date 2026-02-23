/**
 * ChartDisplay — renders a Plotly.js chart from a JSON spec.
 *
 * The agent backend returns Plotly-compatible JSON (data + layout + config).
 * This component uses react-plotly.js to render it interactively client-side.
 */

import React, { lazy, Suspense } from 'react';
import type { PlotlySpec } from '@/types';

// Lazy-load Plotly to keep the initial bundle small
const Plot = lazy(() => import('react-plotly.js'));

interface ChartDisplayProps {
  spec: PlotlySpec;
  title?: string;
  className?: string;
}

export const ChartDisplay: React.FC<ChartDisplayProps> = ({
  spec,
  title,
  className = '',
}) => {
  if (spec.error) {
    return (
      <div className={`chart-error ${className}`}>
        <span>⚠️ Chart error: {spec.error}</span>
      </div>
    );
  }

  return (
    <div className={`chart-container ${className}`}>
      {title && <p className="chart-title">{title}</p>}
      <Suspense fallback={<div className="chart-loading">Loading chart…</div>}>
        <Plot
          data={spec.data as Plotly.Data[]}
          layout={{
            ...(spec.layout as Partial<Plotly.Layout>),
            autosize: true,
          }}
          config={{
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['sendDataToCloud'],
            displaylogo: false,
            ...(spec.config as Partial<Plotly.Config>),
          }}
          style={{ width: '100%', minHeight: 320 }}
          useResizeHandler
        />
      </Suspense>
    </div>
  );
};
