import React, { useState } from 'react';

export default function BarChart({
  data = [],
  height = 220,
  title,
  subtitle
}) {
  const [hovered, setHovered] = useState(null);

  if (!data || data.length === 0) return null;

  const padding = { top: 30, right: 20, bottom: 40, left: 40 };
  const width = 600;

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const maxVal = Math.max(...data.map(d => d.value), 1);
  const barWidth = Math.min(40, (chartWidth / data.length) * 0.6);
  const gap = (chartWidth - (barWidth * data.length)) / (data.length || 1);

  return (
    <div className="card" style={{ width: '100%' }}>
      {(title || subtitle) && (
        <div style={{ marginBottom: '1rem' }}>
          {title && <h3 className="text-lg font-bold">{title}</h3>}
          {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
        </div>
      )}

      <div style={{ position: 'relative', width: '100%', height: '100%' }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', overflow: 'visible' }}>
          <defs>
            {data.map((d, i) => {
              const baseColor = d.color || '#4F46E5';
              return (
                <linearGradient key={`grad-${i}`} id={`bar-grad-${i}`} x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor={baseColor} stopOpacity={hovered === i ? 0.8 : 1} />
                  <stop offset="100%" stopColor={baseColor} stopOpacity={hovered === i ? 0.6 : 0.8} />
                </linearGradient>
              );
            })}
          </defs>

          {/* Y-axis grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map(ratio => {
            const y = padding.top + chartHeight * ratio;
            const val = maxVal - maxVal * ratio;
            return (
              <g key={ratio}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#E5E7EB" strokeWidth="1" strokeDasharray="4 4" />
                <text x={padding.left - 10} y={y + 4} fill="#6B7280" fontSize="10" textAnchor="end">{Math.round(val)}</text>
              </g>
            );
          })}

          {/* Bars */}
          {data.map((d, i) => {
            const x = padding.left + gap/2 + i * (barWidth + gap);
            const barH = (d.value / maxVal) * chartHeight;
            const y = padding.top + chartHeight - barH;
            
            return (
              <g 
                key={i}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Bar Background (optional) */}
                <rect
                  x={x}
                  y={padding.top}
                  width={barWidth}
                  height={chartHeight}
                  fill="transparent"
                />
                
                {/* Actual Bar */}
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barH}
                  fill={`url(#bar-grad-${i})`}
                  rx={4}
                  style={{ transition: 'all 0.2s' }}
                />
                
                {/* Value Label on Top */}
                <text
                  x={x + barWidth / 2}
                  y={y - 8}
                  fill="#374151"
                  fontSize="10"
                  fontWeight="bold"
                  textAnchor="middle"
                  opacity={hovered === i ? 1 : 0.7}
                >
                  {d.value}
                </text>

                {/* X-axis Label */}
                <text
                  x={x + barWidth / 2}
                  y={height - 15}
                  fill="#6B7280"
                  fontSize="10"
                  textAnchor="middle"
                  transform={`rotate(-15, ${x + barWidth / 2}, ${height - 15})`}
                >
                  {d.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
