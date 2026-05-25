# 📊 Frontend Visualizations - Professional Reports

Modern, interactive visualizations for cybersecurity reports using Recharts and D3.

## 🎨 Components Overview

### Core Visualizations

#### 1. **AttackTimelineChart**

Interactive area chart showing attack events over time with severity stacking.

**Features:**

- Stacked area chart (Critical/High/Medium/Low)
- Gradient fills with severity colors
- Interactive brush for zooming
- Hover tooltips with details
- Auto-aggregation by hour

**Usage:**

```tsx
import { AttackTimelineChart } from './visualizations';

<AttackTimelineChart
  timeline={report.attack_timeline}
  height={300}
/>
```

---

#### 2. **GeoDistributionChart**

Bar chart showing top attacking countries with color-coded bars.

**Features:**

- Top N countries (default: 10)
- Color-coded bars
- Angled labels for readability
- Custom tooltips with attack counts and IPs
- Responsive design

**Usage:**

```tsx
import { GeoDistributionChart } from './visualizations';

<GeoDistributionChart
  data={report.geo_distribution}
  height={350}
  topN={10}
/>
```

---

#### 3. **AttackCategoriesChart**

Donut chart showing distribution of attack types.

**Features:**

- Donut/pie chart with inner radius
- Percentage labels
- Legend with percentages
- Color-coded categories
- Interactive tooltips

**Usage:**

```tsx
import { AttackCategoriesChart } from './visualizations';

<AttackCategoriesChart
  categories={report.threat_summary.top_attack_categories}
  height={300}
/>
```

---

#### 4. **SeverityDistributionChart**

Radial bar chart showing severity level distribution.

**Features:**

- Radial bars for each severity level
- Color-coded (Critical=Red, High=Orange, etc.)
- Percentage display
- Responsive legend
- Animated transitions

**Usage:**

```tsx
import { SeverityDistributionChart } from './visualizations';

<SeverityDistributionChart
  summary={report.threat_summary}
  height={300}
/>
```

---

#### 5. **AnimatedMetric**

Animated KPI card with counter effect and trend indicator.

**Features:**

- Smooth number counting animation (0 → value)
- Trend indicators (up/down/neutral)
- Custom icons
- Color theming
- Prefix/suffix support (%, $, etc.)

**Usage:**

```tsx
import { AnimatedMetric } from './visualizations';

<AnimatedMetric
  value={1247}
  label="Total Events"
  icon={<Activity size={24} />}
  color="#00f5ff"
  trend="up"
  trendValue={23}
/>
```

**Props:**

- `value`: number - The metric value
- `label`: string - Metric label
- `icon`: ReactNode - Icon component
- `color`: string - Theme color (CSS variable or hex)
- `trend`: 'up' | 'down' | 'neutral' - Trend direction
- `trendValue`: number - Percentage change
- `suffix`: string - e.g., '%', 'K'
- `prefix`: string - e.g., '$', '€'
- `decimals`: number - Decimal places

---

### Enhanced Report Sections

#### 1. **ThreatOverviewMetrics**

Grid of animated KPI cards showing key threat metrics.

**Shows:**

- Total Events (cyan)
- Unique Attackers (purple)
- Critical Events (red)
- Bot Traffic % (orange)

---

#### 2. **EnhancedAttackAnalytics**

Comprehensive attack analysis with multiple charts.

**Includes:**

- Severity Distribution (radial chart)
- Attack Timeline (area chart)
- Attack Categories (donut chart)

---

#### 3. **EnhancedGeoDistribution**

Geographic analysis with bar chart and detailed table.

**Features:**

- Top countries bar chart
- Detailed data table
- Primary attack types per country

---

## 🎨 Styling

### Color Palette

```css
/* Severity Colors */
--severity-critical: #ff4757
--severity-high: #ff6348
--severity-medium: #ffa502
--severity-low: #26de81

/* Cyber Theme */
--cyber-purple: #9d4edd
--cyber-cyan: #00f5ff
--cyber-blue: #3742fa
--cyber-pink: #f368e0

/* Chart Colors (COLORS array) */
#ff4757, #ff6348, #ffa502, #26de81, #00f5ff, #9d4edd, #3742fa, #f368e0
```

### Custom Classes

```css
.hp-chart-container        /* Chart wrapper with glassmorphism */
.hp-chart-empty            /* Empty state message */
.hp-animated-metric        /* Animated KPI card */
.hp-metric-value           /* Large number display */
.hp-metric-trend           /* Trend indicator badge */
.hp-preview-section-enhanced  /* Enhanced section container */
.hp-metrics-grid           /* Responsive grid for metrics */
```

---

## 📱 Responsive Design

All components are fully responsive:

**Desktop (>1200px):**

- 2-column layout (config + preview)
- Metrics grid: 2-4 columns
- Full chart heights

**Tablet (768px - 1200px):**

- 1-column layout
- Metrics grid: 2 columns
- Adjusted chart heights

**Mobile (<768px):**

- 1-column layout
- Metrics grid: 1 column
- Compact chart sizes
- Stacked sections

---

## 🎯 Integration Example

Complete example integrating all visualizations:

```tsx
import {
  ThreatOverviewMetrics,
  EnhancedExecutiveSummary,
  EnhancedAttackAnalytics,
  EnhancedGeoDistribution,
} from './components/EnhancedReportSections';

function ReportDashboard({ report }: { report: SecurityReport }) {
  return (
    <div className="report-dashboard">
      {/* Animated KPIs */}
      <ThreatOverviewMetrics report={report} />

      {/* AI-Generated Summary */}
      {report.executive_summary && (
        <EnhancedExecutiveSummary content={report.executive_summary} />
      )}

      {/* Charts: Timeline, Categories, Severity */}
      <EnhancedAttackAnalytics report={report} />

      {/* Geographic Analysis */}
      {report.geo_distribution && (
        <EnhancedGeoDistribution data={report.geo_distribution} />
      )}
    </div>
  );
}
```

---

## 🔧 Customization

### Chart Heights

All charts accept a `height` prop (default: 300-350px):

```tsx
<AttackTimelineChart timeline={data} height={400} />
<GeoDistributionChart data={data} height={500} topN={15} />
```

### Color Themes

Override chart colors via props or CSS variables:

```tsx
<AnimatedMetric
  value={1000}
  label="Custom Metric"
  color="#custom-color"
/>
```

### Custom Tooltips

All Recharts components use custom tooltips with dark theme:

```tsx
const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.95)', ... }}>
        {/* Custom content */}
      </div>
    );
  }
  return null;
};
```

---

## 📦 Dependencies

```json
{
  "recharts": "^3.6.0",      // Main charting library
  "d3": "^7.9.0",            // Data manipulation (future use)
  "react": "^18.x",
  "lucide-react": "^0.263.1" // Icons
}
```

---

## 🚀 Performance

### Optimization Techniques

1. **useMemo for data transformation**

   ```tsx
   const chartData = useMemo(() => {
     return processData(rawData);
   }, [rawData]);
   ```

2. **Animation duration control**

   ```tsx
   <Area animationDuration={800} />  // Fast transitions
   ```

3. **Conditional rendering**

   ```tsx
   {data?.length > 0 && <Chart data={data} />}
   ```

4. **CSS animations instead of JS**

   ```css
   @keyframes slideDown { ... }
   .hp-metric-value { animation: slideDown 0.5s; }
   ```

---

## 🎨 Design Principles

### Glassmorphism

All chart containers use glassmorphism effect:

- Semi-transparent backgrounds
- Backdrop blur (10-16px)
- Subtle borders
- Box shadows for depth

### Cyber Theme

Consistent with honeypot dashboard:

- Purple/cyan color scheme
- Glowing effects on hover
- Dark background with gradients
- Monospace fonts for data

### Accessibility

- High contrast colors
- Readable font sizes (11-13pt)
- Clear labels and legends
- Hover states for interactivity

---

## 🔮 Future Enhancements

### Phase 2 (Next)

- [ ] D3 Geographic Heatmap (world map with intensity)
- [ ] Force-directed Botnet Graph (network visualization)
- [ ] 3D Threat Landscape (Plotly.js)
- [ ] Real-time data streaming charts

### Phase 3 (Advanced)

- [ ] Export charts as PNG/SVG
- [ ] Chart theme switcher (dark/light)
- [ ] Custom chart builder UI
- [ ] Animation timeline controls
- [ ] WebGL-accelerated large datasets

---

## 📚 Resources

**Recharts Docs:** <https://recharts.org/>
**D3 Gallery:** <https://observablehq.com/@d3/gallery>
**Lucide Icons:** <https://lucide.dev/>
**Color Palettes:** <https://coolors.co/>

---

## 🐛 Troubleshooting

### Chart not rendering

- Ensure data is not null/undefined
- Check data format matches expected structure
- Verify ResponsiveContainer has a parent with height

### Animation not working

- Check `animationDuration` prop
- Ensure component rerenders on data change
- CSS animations require proper keyframes

### Tooltip not showing

- Verify `Tooltip` component is included
- Check z-index conflicts
- Ensure proper event handling

---

## ✅ Testing

Run frontend dev server:

```bash
cd frontend/apps/honeypot
npm run dev
```

Navigate to Reports tab and generate preview to see all visualizations.

---

## 🎉 Result

Professional, interactive reports that rival **CrowdStrike**, **Splunk**, and **Palo Alto Networks** dashboards!

All visualizations are:
✅ Responsive
✅ Animated
✅ Interactive
✅ Cyber-themed
✅ Performance-optimized
