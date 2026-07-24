import ReactECharts from "echarts-for-react";

const DARK = {
  backgroundColor: "transparent",
  textStyle: { color: "#cbd5e1" },
  color: ["#3b82f6", "#f59e0b", "#10b981", "#a78bfa", "#ef4444"],
};

export default function Chart({ option, height = 280 }) {
  const merged = {
    ...DARK,
    ...option,
    xAxis: option.xAxis && {
      axisLabel: { color: "#94a3b8" },
      axisLine: { lineStyle: { color: "#334155" } },
      ...option.xAxis,
    },
    yAxis: option.yAxis && {
      axisLabel: { color: "#94a3b8" },
      splitLine: { lineStyle: { color: "#1e293b" } },
      ...option.yAxis,
    },
  };
  return <ReactECharts option={merged} style={{ height }} notMerge />;
}
