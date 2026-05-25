/**
 * Section Selector Component
 *
 * Multi-select interface for choosing report sections.
 */

import { CheckCircle } from 'lucide-react';
import { ReportSection } from '../../../types';
import { SECTION_ICONS } from '../ReportsConstants';

interface SectionSelectorProps {
  sections: ReportSection[];
  selectedSections: ReportSection[];
  onSectionsChange: (sections: ReportSection[]) => void;
}

export function SectionSelector({
  sections,
  selectedSections,
  onSectionsChange,
}: SectionSelectorProps) {
  const toggleSection = (section: ReportSection) => {
    onSectionsChange(
      selectedSections.includes(section)
        ? selectedSections.filter((s) => s !== section)
        : [...selectedSections, section]
    );
  };

  const toggleAll = () => {
    if (selectedSections.length === sections.length) {
      onSectionsChange([]);
    } else {
      onSectionsChange(sections);
    }
  };

  const allSelected = selectedSections.length === sections.length;

  return (
    <div className="section-selector">
      <div className="section-header">
        <label className="config-label">Report Sections</label>
        <button className="toggle-all-btn" onClick={toggleAll}>
          {allSelected ? 'Deselect All' : 'Select All'}
        </button>
      </div>

      <div className="sections-grid">
        {sections.map((section) => {
          const Icon = SECTION_ICONS[section];
          const isSelected = selectedSections.includes(section);

          return (
            <button
              key={section}
              className={`section-card ${isSelected ? 'selected' : ''}`}
              onClick={() => toggleSection(section)}
            >
              {Icon && <Icon size={18} />}
              <span className="section-name">
                {section.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              </span>
              {isSelected && <CheckCircle size={18} className="check-icon" />}
            </button>
          );
        })}
      </div>

      {selectedSections.length === 0 && (
        <div className="section-warning">
          ⚠️ Please select at least one section to generate a report
        </div>
      )}
    </div>
  );
}
