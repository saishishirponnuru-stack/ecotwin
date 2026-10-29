import React from 'react';
import EChartsReactCore from 'echarts-for-react/esm/core';
import { echarts } from './echarts';
import { useTheme } from '../../theme/useTheme';

interface DailyEnergyChartProps {
  data: {
    dates: string[];
    actual: number[];
    baseline: number[];
  };
  comparisonLabel?: string;
}

const DailyEnergyChart: React.FC<DailyEnergyChartProps> = ({ data, comparisonLabel = 'Analytical baseline' }) => {
  const { theme } = useTheme();
  const palette = theme === 'dark'
    ? { panel: '#1f2937', tooltip: '#111827', text: '#e5e7eb', muted: '#9ca3af', axis: '#64748b', grid: '#374151', accent: '#2dd4bf', comparison: '#10b981' }
    : { panel: '#ffffff', tooltip: '#ffffff', text: '#0f172a', muted: '#475569', axis: '#64748b', grid: '#e2e8f0', accent: '#0f766e', comparison: '#047857' };
  const option = {
    backgroundColor: palette.panel,
    textStyle: { color: palette.text },
    tooltip: {
      trigger: 'axis',
      backgroundColor: palette.tooltip,
      borderColor: palette.grid,
      textStyle: { color: palette.text },
      axisPointer: { lineStyle: { color: palette.axis } },
    },
    title: { text: `Daily Derived Energy vs ${comparisonLabel}`, textStyle: { color: palette.text, fontSize: 14 } },
    legend: {
      data: ['Derived energy', comparisonLabel],
      textStyle: { color: palette.text },
    },
    xAxis: {
      type: 'category',
      data: data.dates,
      axisLabel: { color: palette.muted, formatter: (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) },
      axisLine: { lineStyle: { color: palette.axis } },
      axisTick: { lineStyle: { color: palette.axis } },
    },
    yAxis: {
      type: 'value',
      name: 'kWh',
      nameTextStyle: { color: palette.muted },
      axisLabel: { color: palette.muted, formatter: '{value} kWh' },
      axisLine: { lineStyle: { color: palette.axis } },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    series: [
      {
        name: 'Derived energy',
        type: 'line',
        data: data.actual,
        smooth: true,
        lineStyle: { color: palette.accent },
        itemStyle: { color: palette.accent },
      },
      {
        name: comparisonLabel,
        type: 'line',
        data: data.baseline,
        smooth: true,
        lineStyle: { color: palette.comparison },
        itemStyle: { color: palette.comparison },
      },
    ],
  };

  return <EChartsReactCore key={theme} echarts={echarts} option={option} notMerge={true} style={{ height: 'clamp(260px, 44vw, 400px)', width: '100%' }} lazyUpdate={true} autoResize={true} />;
};

export default DailyEnergyChart;
