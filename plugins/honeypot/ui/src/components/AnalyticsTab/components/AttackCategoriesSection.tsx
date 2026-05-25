import { Zap } from 'lucide-react';
import { CategoryCard } from './CategoryCard';

interface CategoryData {
  category: string;
  count: number;
  percentage: number;
  icon: React.ReactNode;
  color: string;
}

interface AttackCategoriesSectionProps {
  categoryData: CategoryData[];
}

export function AttackCategoriesSection({ categoryData }: AttackCategoriesSectionProps) {
  return (
    <div className="analytics-section-card">
      <h3 className="analytics-section-title">
        <Zap size={18} /> Attack Categories
      </h3>
      <div className="analytics-categories-grid">
        {categoryData.map((cat, idx) => (
          <CategoryCard key={idx} {...cat} />
        ))}
        {categoryData.length === 0 && (
          <div className="analytics-empty">No attack categories yet</div>
        )}
      </div>
    </div>
  );
}
