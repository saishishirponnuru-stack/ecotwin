import React from 'react';
import EChartsReactCore from 'echarts-for-react/esm/core';
import { echarts } from './echarts';
import { useTheme } from '../../theme/useTheme';

interface Machine {
  id: string;
  avg_sec: number;
}

interface MachinePerformanceChartProps {
  machines: Machine[];
}

const MachinePerformanceChart: React.FC<MachinePerformanceChartProps> = ({ machines }) => {
  const { theme } = useTheme();
  const palette = theme === 'dark'
    ? { panel: '#1f2937', tooltip: '#111827', text: '#e5e7eb', muted: '#9ca3af', axis: '#64748b', grid: '#374151', accent: '#2dd4bf' }
    : { panel: '#ffffff', tooltip: '#ffffff', text: '#0f172a', muted: '#475569', axis: '#64748b', grid: '#e2e8f0', accent: '#0f766e' };
  const option = {
    backgroundColor: palette.panel,
    textStyle: { color: palette.text },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: theme === 'dark' ? 'rgba(148, 163, 184, 0.12)' : 'rgba(15, 23, 42, 0.08)' } },
      backgroundColor: palette.tooltip,
      borderColor: palette.grid,
      textStyle: { color: palette.text },
    },
    title: { text: 'Machine Energy Intensity', textStyle: { color: palette.text, fontSize: 14 } },
    legend: { data: ['Energy intensity'], textStyle: { color: palette.text } },
    xAxis: {
      type: 'category',
      data: machines.map(m => m.id),
      axisLabel: { color: palette.muted },
      axisLine: { lineStyle: { color: palette.axis } },
      axisTick: { lineStyle: { color: palette.axis } },
    },
    yAxis: {
      type: 'value',
      name: 'kWh/part',
      nameTextStyle: { color: palette.muted },
      axisLabel: { color: palette.muted },
      axisLine: { lineStyle: { color: palette.axis } },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    series: [
      {
        name: 'Energy intensity',
        type: 'bar',
        data: machines.map(m => m.avg_sec),
        itemStyle: { color: palette.accent },
      },
    ],
  };

  return <EChartsReactCore key={theme} echarts={echarts} option={option} notMerge={true} style={{ height: 'clamp(240px, 32vw, 300px)', width: '100%' }} autoResize={true} />;
};

export default MachinePerformanceChart;
