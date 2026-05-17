import { Area, AreaChart, ResponsiveContainer } from "recharts";

interface Props {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  gradientId?: string;
}

export function Sparkline({
  data,
  width = 80,
  height = 22,
  color = "#10b981",
  gradientId,
}: Props) {
  const id = gradientId ?? `sparkline-${color.replace("#", "")}`;
  const series = (data.length ? data : [0, 0]).map((v, i) => ({ i, v }));
  return (
    <div style={{ width, height }} className="inline-block">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={series} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.4} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#${id})`}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
