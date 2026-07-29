import React, { useState } from 'react';

// ============================================================================
// 1. PURE SVG LINE CHART
// ============================================================================
interface LineChartPoint {
  label: string;
  value: number;
}

interface LineChartProps {
  data: LineChartPoint[];
  height?: number;
  color?: string;
  fillGradient?: boolean;
}

export const LineChart: React.FC<LineChartProps> = ({
  data,
  height = 200,
  color = '#4F46E5',
  fillGradient = true
}) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!data || data.length === 0) return null;

  const width = 600;
  const padding = 30;
  const maxVal = Math.max(...data.map((d) => d.value)) * 1.15 || 100;
  const minVal = Math.min(...data.map((d) => d.value)) * 0.85 || 0;

  const pointsX = data.map((_, i) => padding + (i / (data.length - 1)) * (width - padding * 2));
  const pointsY = data.map((d) => height - padding - ((d.value - minVal) / (maxVal - minVal)) * (height - padding * 2));

  // Construct SVG Path
  const pathD = pointsX.reduce((acc, x, i) => {
    const y = pointsY[i];
    return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, '');

  const areaD = `${pathD} L ${pointsX[pointsX.length - 1]} ${height - padding} L ${pointsX[0]} ${height - padding} Z`;

  return (
    <div className="w-full relative">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
        <defs>
          <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.35" />
            <stop offset="100%" stopColor={color} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {[0, 0.33, 0.66, 1].map((pct, idx) => {
          const y = padding + pct * (height - padding * 2);
          return (
            <line
              key={idx}
              x1={padding}
              y1={y}
              x2={width - padding}
              y2={y}
              stroke="#1F2937"
              strokeDasharray="4 4"
              strokeWidth="1"
            />
          );
        })}

        {/* Area Gradient */}
        {fillGradient && <path d={areaD} fill="url(#lineGrad)" />}

        {/* Line */}
        <path d={pathD} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />

        {/* Data Dots & Hover */}
        {data.map((d, i) => {
          const x = pointsX[i];
          const y = pointsY[i];
          const isHovered = hoveredIdx === i;
          return (
            <g key={i} onMouseEnter={() => setHoveredIdx(i)} onMouseLeave={() => setHoveredIdx(null)}>
              <circle
                cx={x}
                cy={y}
                r={isHovered ? 6 : 4}
                fill={isHovered ? '#FFFFFF' : color}
                stroke={color}
                strokeWidth="2"
                className="cursor-pointer transition-all duration-150"
              />

              {/* X Axis Label */}
              <text x={x} y={height - 8} fill="#6B7280" fontSize="10" textAnchor="middle" className="font-mono select-none">
                {d.label}
              </text>

              {/* Hover Tooltip */}
              {isHovered && (
                <g>
                  <rect
                    x={x - 40}
                    y={y - 32}
                    width="80"
                    height="24"
                    rx="6"
                    fill="#111827"
                    stroke="#374151"
                    strokeWidth="1"
                  />
                  <text x={x} y={y - 16} fill="#F9FAFB" fontSize="11" fontWeight="bold" textAnchor="middle" className="font-mono">
                    {d.value.toLocaleString()}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
};

// ============================================================================
// 2. PURE SVG DONUT CHART
// ============================================================================
interface DonutSegment {
  label: string;
  value: number;
  color: string;
}

interface DonutChartProps {
  data: DonutSegment[];
  size?: number;
  centerText?: string;
  centerSubtext?: string;
}

export const DonutChart: React.FC<DonutChartProps> = ({
  data,
  size = 200,
  centerText,
  centerSubtext
}) => {
  const total = data.reduce((acc, d) => acc + d.value, 0) || 1;
  const radius = 70;
  const strokeWidth = 24;
  const circumference = 2 * Math.PI * radius;

  let cumulativeOffset = 0;

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6">
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg viewBox="0 0 200 200" className="w-full h-full transform -rotate-90">
          {data.map((seg, i) => {
            const strokeDasharray = (seg.value / total) * circumference;
            const strokeDashoffset = -cumulativeOffset;
            cumulativeOffset += strokeDasharray;

            return (
              <circle
                key={i}
                cx="100"
                cy="100"
                r={radius}
                fill="none"
                stroke={seg.color}
                strokeWidth={strokeWidth}
                strokeDasharray={`${strokeDasharray} ${circumference - strokeDasharray}`}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-300 hover:opacity-80 cursor-pointer"
              />
            );
          })}
        </svg>

        {/* Center Label */}
        {(centerText || centerSubtext) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            {centerText && <span className="text-xl font-black text-white font-mono">{centerText}</span>}
            {centerSubtext && <span className="text-[10px] uppercase font-bold text-slate-400">{centerSubtext}</span>}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="space-y-2 text-xs flex-1">
        {data.map((seg, i) => {
          const pct = Math.round((seg.value / total) * 100);
          return (
            <div key={i} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-2 text-slate-300 font-medium">
                <span className="w-3 h-3 rounded-md shrink-0" style={{ backgroundColor: seg.color }} />
                {seg.label}
              </span>
              <span className="font-mono font-bold text-slate-100">{pct}% ({seg.value.toLocaleString()})</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================================
// 3. PURE SVG BAR CHART
// ============================================================================
interface BarItem {
  label: string;
  value: number;
  color?: string;
}

interface BarChartProps {
  data: BarItem[];
  height?: number;
  defaultColor?: string;
}

export const BarChart: React.FC<BarChartProps> = ({
  data,
  height = 180,
  defaultColor = '#4F46E5'
}) => {
  if (!data || data.length === 0) return null;

  const maxVal = Math.max(...data.map((d) => d.value)) * 1.15 || 100;

  return (
    <div className="w-full flex items-end gap-3 pt-6 pb-2" style={{ height }}>
      {data.map((item, i) => {
        const barHeightPct = Math.max((item.value / maxVal) * 100, 4);
        const barColor = item.color || defaultColor;

        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-2 group h-full justify-end">
            <span className="text-[10px] font-mono font-bold text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">
              {item.value}%
            </span>
            <div className="w-full bg-[#1F2937] rounded-t-xl overflow-hidden flex items-end" style={{ height: '100%' }}>
              <div
                className="w-full rounded-t-xl transition-all duration-500 group-hover:brightness-125"
                style={{ height: `${barHeightPct}%`, backgroundColor: barColor }}
              />
            </div>
            <span className="text-[11px] font-medium text-slate-400 truncate w-full text-center">
              {item.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};
