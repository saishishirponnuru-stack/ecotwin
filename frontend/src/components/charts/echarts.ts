import * as echarts from 'echarts/core';
import { BarChart, LineChart } from 'echarts/charts';
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

// Register only the chart types and components used by EcoTwin. Importing the
// default ECharts bundle adds unused chart families to the deferred chart chunk.
echarts.use([
  BarChart,
  LineChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  CanvasRenderer,
]);

export { echarts };
