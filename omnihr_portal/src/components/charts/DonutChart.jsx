import React, { useState } from 'react';

export default function DonutChart({
  data = [],
  size = 200,
  title,
  subtitle
}) {
  const [hovered, setHovered] = useState(null);

  if (!data || data.length === 0) return null;

  const total = data.reduce((acc, curr) => acc + curr.value, 0);
  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.35;
  const strokeWidth = size * 0.15;

  let currentAngle = -90; // Start at top

  const createArc = (startAngle, endAngle, isHovered) => {
    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;
    
    // Slight gap adjustment
    const gap = 2; // degrees
    const actualStart = startAngle + gap / 2;
    const actualEnd = endAngle - gap / 2;
    
    if (actualEnd <= actualStart) return '';

    const sRad = (actualStart * Math.PI) / 180;
    const eRad = (actualEnd * Math.PI) / 180;

    const r = isHovered ? radius * 1.05 : radius;
    
    const x1 = cx + r * Math.cos(sRad);
    const y1 = cy + r * Math.sin(sRad);
    const x2 = cx + r * Math.cos(eRad);
    const y2 = cy + r * Math.sin(eRad);

    const largeArcFlag = actualEnd - actualStart <= 180 ? 0 : 1;

    return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArcFlag} 1 ${x2} ${y2}`;
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
      {(title || subtitle) && (
        <div style={{ width: '100%', marginBottom: '1rem' }}>
          {title && <h3 className="text-lg font-bold">{title}</h3>}
          {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: '2rem' }}>
        <div style={{ position: 'relative', width: size, height: size }}>
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            {data.map((item, i) => {
              const angle = (item.value / total) * 360;
              const start = currentAngle;
              const end = currentAngle + angle;
              currentAngle = end;

              const isHovered = hovered === i;
              const path = createArc(start, end, isHovered);

              return (
                <path
                  key={i}
                  d={path}
                  fill="none"
                  stroke={item.color || '#4F46E5'}
                  strokeWidth={isHovered ? strokeWidth * 1.1 : strokeWidth}
                  style={{ transition: 'all 0.2s ease', cursor: 'pointer' }}
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}
                />
              );
            })}
          </svg>
          
          <div style={{
            position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', pointerEvents: 'none'
          }}>
            <span className="text-muted text-xs">Total</span>
            <span className="font-bold text-lg">{total}</span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {data.map((item, i) => {
            const percentage = ((item.value / total) * 100).toFixed(1);
            return (
              <div 
                key={i} 
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', opacity: hovered !== null && hovered !== i ? 0.5 : 1, transition: 'opacity 0.2s' }}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
              >
                <div style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: item.color || '#4F46E5' }}></div>
                <span className="text-sm font-bold" style={{ width: '80px' }}>{item.label}</span>
                <span className="text-sm text-muted">{item.value} ({percentage}%)</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
