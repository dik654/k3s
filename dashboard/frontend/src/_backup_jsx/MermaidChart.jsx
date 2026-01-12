import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

// Mermaid 초기화
mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  securityLevel: 'loose',
  flowchart: {
    useMaxWidth: true,
    htmlLabels: true,
    curve: 'basis'
  },
  themeVariables: {
    primaryColor: '#3b82f6',
    primaryTextColor: '#18181b',
    primaryBorderColor: '#2563eb',
    lineColor: '#71717a',
    secondaryColor: '#f4f4f5',
    tertiaryColor: '#fafafa',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  }
});

const MermaidChart = ({ chart, className = '' }) => {
  const containerRef = useRef(null);
  const idRef = useRef(`mermaid-${Math.random().toString(36).substr(2, 9)}`);

  useEffect(() => {
    if (containerRef.current && chart) {
      const renderChart = async () => {
        try {
          containerRef.current.innerHTML = '';
          const { svg } = await mermaid.render(idRef.current, chart);
          containerRef.current.innerHTML = svg;
        } catch (error) {
          console.error('Mermaid render error:', error);
          containerRef.current.innerHTML = `<div class="mermaid-error">차트 렌더링 실패</div>`;
        }
      };
      renderChart();
    }
  }, [chart]);

  return (
    <div
      ref={containerRef}
      className={`mermaid-container ${className}`}
    />
  );
};

export default MermaidChart;
