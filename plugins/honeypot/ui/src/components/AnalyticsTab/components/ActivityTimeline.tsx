import { Clock } from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface ActivityData {
  time: string;
  count: number;
}

interface ActivityTimelineProps {
  activityHistory: ActivityData[];
}

export function ActivityTimeline({ activityHistory }: ActivityTimelineProps) {
  return (
    <div className="analytics-timeline-section">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}
      >
        <h3 className="analytics-section-title" style={{ margin: 0 }}>
          <Clock size={18} /> Attack Activity
        </h3>
        <span className="analytics-live-tag">
          <span className="pulse-dot"></span> LIVE
        </span>
      </div>
      <div className="analytics-chart-container" style={{ height: 250, width: '100%' }}>
        {activityHistory && activityHistory.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={100}>
            <AreaChart data={activityHistory} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ff4757" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#ff4757" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.1)"
                vertical={false}
              />
              <XAxis
                dataKey="time"
                tickFormatter={(timeStr) => {
                  try {
                    return new Date(timeStr).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    });
                  } catch (e) {
                    return timeStr;
                  }
                }}
                stroke="#8395a7"
                tick={{ fill: '#8395a7', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                minTickGap={30}
              />
              <YAxis
                stroke="#8395a7"
                tick={{ fill: '#8395a7', fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(20, 20, 30, 0.95)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
                }}
                itemStyle={{ color: '#fff', fontSize: '13px' }}
                labelStyle={{ color: '#8892b0', marginBottom: '8px', fontSize: '12px' }}
                labelFormatter={(label) => {
                  try {
                    return new Date(label).toLocaleString();
                  } catch (e) {
                    return label;
                  }
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#ff4757"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorCount)"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="chart-placeholder-container">
            <div className="chart-placeholder-grid" />
            <div className="chart-pulse-line">
              <div className="chart-pulse-activity" />
            </div>
            <div className="chart-placeholder-text">Listening for activity...</div>
          </div>
        )}
      </div>
    </div>
  );
}
