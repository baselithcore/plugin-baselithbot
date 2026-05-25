import React, { useState } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

const ExpandableSection: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}> = ({ title, icon, children, defaultExpanded = true }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <section className="hp-section hp-section--expandable">
      <h3 onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer' }}>
        {icon} {title}
        <span className="hp-section-toggle">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </h3>
      {expanded && <div className="hp-section-content">{children}</div>}
    </section>
  );
};

export default ExpandableSection;
