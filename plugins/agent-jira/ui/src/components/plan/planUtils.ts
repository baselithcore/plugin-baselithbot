import { UserStoryPayload } from '../../types';

export const priorityTone = (value?: string): string => {
  const val = (value || '').toLowerCase();
  if (val.includes('highest') || val === 'blocker' || val === 'critical') return 'priority-highest';
  if (val.includes('high')) return 'priority-high';
  if (val.includes('medium') || val.includes('should')) return 'priority-medium';
  if (val.includes('low') || val.includes('could')) return 'priority-low';
  return 'priority-neutral';
};

export const sortStoriesByPriority = (stories: UserStoryPayload[]) => {
  const rank = (val?: string) => {
    if (!val) return 5;
    const v = val.toLowerCase();
    if (v === 'highest' || v === 'blocker' || v === 'critical') return 0;
    if (v === 'high') return 1;
    if (v === 'medium' || v === 'should') return 2;
    if (v === 'low' || v === 'could') return 3;
    return 4;
  };
  return [...stories].sort((a, b) => rank(a.priority) - rank(b.priority));
};

export const storyBusinessValue = (story: UserStoryPayload) => {
  const businessValues = Array.isArray(story.business_value)
    ? story.business_value
        .filter((val) => typeof val === 'string' && val.trim().length > 0)
        .map((val) => val.trim())
    : [];
  const benefitNormalized = (story.benefit || '').trim().toLowerCase();
  const distinctValues = businessValues.filter((val, idx, arr) => arr.indexOf(val) === idx);
  const limitedValues = distinctValues.slice(0, 3);
  const primaryBusinessValue =
    limitedValues.find((val) => val.trim().toLowerCase() !== benefitNormalized) ||
    limitedValues[0] ||
    story.benefit ||
    'Non definito';

  return { businessValues: limitedValues, primaryBusinessValue };
};
