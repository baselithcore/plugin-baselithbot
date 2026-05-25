import DonutChart from '../../charts/DonutChart';

interface ChartData {
  label: string;
  value: number;
  color: string;
}

interface ChartsRowProps {
  protocolData: ChartData[];
  botData: ChartData[];
  severityData: ChartData[];
}

export function ChartsRow({ protocolData, botData, severityData }: ChartsRowProps) {
  return (
    <div className="analytics-charts-row">
      <div className="analytics-chart-card">
        <DonutChart data={protocolData} title="Protocol Distribution" />
      </div>
      <div className="analytics-chart-card">
        <DonutChart data={botData} title="Bot vs Human" />
      </div>
      <div className="analytics-chart-card">
        <DonutChart data={severityData} title="Severity Distribution" />
      </div>
    </div>
  );
}
