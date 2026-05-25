import { clsx } from 'clsx';

interface TabItem<T extends string> {
  id: T;
  label: string;
  disabled?: boolean;
}

interface TabsProps<T extends string> {
  tabs: TabItem<T>[];
  active: T;
  onChange: (tab: T) => void;
}

const Tabs = <T extends string>({ tabs, active, onChange }: TabsProps<T>) => {
  return (
    <div className="tabs">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={clsx('tab', active === tab.id && 'tab-active', tab.disabled && 'tab-disabled')}
          disabled={tab.disabled}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
};

export default Tabs;
