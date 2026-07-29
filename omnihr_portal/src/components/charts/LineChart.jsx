import React, { useState } from 'react';

export default function LineChart({
  data = [],
  height = 200,
  color = '#4F46E5',
  title,
  subtitle
}) {
  const [hovered, setHovered] = useState(null);

  if (!data || data.length === 0) return null;

  const padding = { top: 20, right: 20, bottom: 30, left: 40 };
  const width = 600; // SVG viewBox width

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const minVal = Math.min(...data.map(d => d.value), 0);
  const maxVal = Math.max(...data.map(d => d.value));
  
  const getX = (index) => padding.left + (index / (data.length - 1 || 1)) * chartWidth;
  const getY = (val) => padding.top + chartHeight - ((val - minVal) / (maxVal - minVal || 1)) * chartHeight;

  // Generate smooth bezier curve path
  const generatePath = () => {
    if (data.length === 0) return '';
    if (data.length === 1) return `M ${getX(0)} ${getY(data[0].value)}`;
    
    let d = `M ${getX(0)} ${getY(data[0].value)}`;
    for (let i = 0; i < data.length - 1; i++) {
      const x1 = getX(i);
      const y1 = getY(data[i].value);
      const x2 = getX(i + 1);
      const y2 = getY(data[i+1].value);
      
      const cx1 = x1 + (x2 - x1) / 3;
      const cx2 = x2 - (x2 - x1) / 3;
      
      d += ` C ${cx1} ${y1}, ${cx2} ${y2}, ${x2} ${y2}`;
    }
    return d;
  };

  const linePath = generatePath();
  
  // Area path (closed path for gradient fill)
  const areaPath = `${linePath} L ${getX(data.length - 1)} ${padding.top + chartHeight} L ${getX(0)} ${padding.top + chartHeight} Z`;

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
            <linearGradient id="line-gradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>

          {/* Y-axis grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map(ratio => {
            const y = padding.top + chartHeight * ratio;
            const val = maxVal - (maxVal - minVal) * ratio;
            return (
              <g key={ratio}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#E5E7EB" strokeWidth="1" />
                <text x={padding.left - 10} y={y + 4} fill="#6B7280" fontSize="10" textAnchor="end">{Math.round(val)}</text>
              </g>
            );
          })}

          {/* X-axis labels */}
          {data.map((d, i) => (
            <text key={i} x={getX(i)} y={height - 10} fill="#6B7280" fontSize="10" textAnchor="middle">
              {d.label}
            </text>
          ))}

          {/* Area fill */}
          <path d={areaPath} fill="url(#line-gradient)" />

          {/* Line */}
          <path d={linePath} fill="none" stroke={color} strokeWidth="2" />

          {/* Points & Tooltips */}
          {data.map((d, i) => {
            const cx = getX(i);
            const cy = getY(d.value);
            const isHovered = hovered === i;
            
            return (
              <g key={i} onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 6 : 4}
                  fill="#ffffff"
                  stroke={color}
                  strokeWidth="2"
                  style={{ transition: 'all 0.2s', cursor: 'pointer' }}
                />
                
                {isHovered && (
                  <g style={{ pointerEvents: 'none' }}>
                    <rect
                      x={cx - 40}
                      y={cy - 45}
                      width="80"
                      height="35"
                      rx="4"
                      fill="#1F2937"
                    />
                    <text x={cx} y={cy - 30} fill="#ffffff" fontSize="10" textAnchor="middle" fontWeight="bold">
                      {d.value}
                    </text>
                    <text x={cx} y={cy - 18} fill="#9CA3AF" fontSize="9" textAnchor="middle">
                      {d.label}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
