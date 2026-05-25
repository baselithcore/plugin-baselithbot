interface CategoryCardProps {
  category: string;
  count: number;
  percentage: number;
  icon: React.ReactNode;
  color: string;
}

export const CategoryCard: React.FC<CategoryCardProps> = ({
  category,
  count,
  percentage,
  icon,
  color,
}) => (
  <div className="analytics-category-card">
    <div className="analytics-category-header">
      <div className="analytics-category-icon" style={{ color }}>
        {icon}
      </div>
      <span className="analytics-category-name">{category.replace(/_/g, ' ')}</span>
    </div>
    <div className="analytics-category-stats">
      <span className="analytics-category-count">{count}</span>
      <div className="analytics-category-bar">
        <div
          className="analytics-category-fill"
          style={{ width: `${percentage}%`, background: color }}
        />
      </div>
    </div>
  </div>
);
