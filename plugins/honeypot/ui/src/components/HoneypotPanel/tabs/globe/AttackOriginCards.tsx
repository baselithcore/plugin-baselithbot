/**
 * AttackOriginCards - Card list with scroll for attack origins
 */

import { RefObject } from 'react';
import { Clock, MapPin, ChevronLeftCircle, ChevronRightCircle } from 'lucide-react';
import type { AttackEvent, HoneypotAttacker } from '../../../types';
import type { DisplayItem } from './types';
import { normalizeIpDisplay } from '../../../api';
import { getCountryFlag } from '../../../geoUtils';
import { getSeverityClass } from '../../utils';
import BotIndicator from '../../../common/BotIndicator';
import * as api from '../../../api';
import { createSyntheticEvent } from './utils';

interface AttackOriginCardsProps {
  items: DisplayItem[];
  onSelectAttack: (event: AttackEvent) => void;
  cardsContainerRef: RefObject<HTMLDivElement>;
  scrollCards: (direction: 'left' | 'right') => void;
  selectedHoneypotId: string | null;
}

export function AttackOriginCards({
  items,
  onSelectAttack,
  cardsContainerRef,
  scrollCards,
  selectedHoneypotId,
}: AttackOriginCardsProps) {
  return (
    <div className="hp-origins-scroll-container">
      {/* Left Scroll Arrow */}
      {items.length > 3 && (
        <button
          className="hp-origins-scroll-btn hp-origins-scroll-btn--left"
          onClick={() => scrollCards('left')}
          title="Scroll left"
        >
          <ChevronLeftCircle size={24} />
        </button>
      )}

      <div className="hp-origins-cards" ref={cardsContainerRef}>
        {items.slice(0, 20).map((item) => {
          // Adapt item to display properties
          const countryCode =
            (item.data as any).country_code || (item.data as any).geo?.country_code;
          const flag = countryCode ? getCountryFlag(countryCode) : '❓';

          // Asynchronous select handler to fetch real event detail
          const handleSelect = async () => {
            if (item.type === 'event') {
              onSelectAttack(item.data as AttackEvent);
            } else {
              const a = item.data as HoneypotAttacker;

              // Attempt to fetch latest real event for this IP to show full details (payload, etc.)
              try {
                const eventData = await api.fetchEvents(1, 1, { source_ip: a.ip });
                if (eventData.items && eventData.items.length > 0) {
                  onSelectAttack(eventData.items[0]);
                  return;
                }
              } catch (e) {
                console.error('Failed to fetch real event for attacker:', e);
              }

              // Fallback to synthetic event if fetch fails or no events found
              const synthEvent = createSyntheticEvent(a, 'attacker');
              onSelectAttack(synthEvent);
            }
          };

          return (
            <div
              key={item.id}
              className={`hp-origin-card ${getSeverityClass(item.severity)}`}
              onClick={handleSelect}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && handleSelect()}
            >
              {/* Card Header with Protocol Badge */}
              <div className="hp-origin-card-header">
                <span className={`hp-origin-protocol-badge protocol-${item.protocol}`}>
                  {item.protocol.toUpperCase()}
                </span>
                <span className={`hp-origin-severity-badge ${getSeverityClass(item.severity)}`}>
                  {item.severity.toUpperCase()}
                </span>
              </div>

              {/* Main Content: Flag + IP */}
              <div className="hp-origin-card-body">
                <div className="hp-origin-location">
                  <span className="hp-origin-flag" title={item.country}>
                    {flag}
                  </span>
                  <div className="hp-origin-details">
                    <span className="hp-origin-ip">{normalizeIpDisplay(item.ip)}</span>
                    <span className="hp-origin-country">{item.country}</span>
                  </div>
                </div>
              </div>

              {/* Card Footer: Time + Bot Status */}
              <div className="hp-origin-card-footer">
                <div className="hp-origin-time-wrapper">
                  <Clock size={10} />
                  <span className="hp-origin-time">
                    {new Date(item.timestamp).toLocaleString([], {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
                {/* Bot/Human Indicator */}
                <BotIndicator
                  isBot={item.is_bot}
                  confidence={item.confidence}
                  size="small"
                  showLabel={false}
                />
              </div>
            </div>
          );
        })}

        {items.length === 0 && (
          <div className="hp-origins-empty">
            <MapPin size={16} />
            <span>
              {selectedHoneypotId ? 'No attacks for this honeypot yet' : 'Waiting for attacks...'}
            </span>
          </div>
        )}
      </div>

      {/* Right Scroll Arrow */}
      {items.length > 3 && (
        <button
          className="hp-origins-scroll-btn hp-origins-scroll-btn--right"
          onClick={() => scrollCards('right')}
          title="Scroll right"
        >
          <ChevronRightCircle size={24} />
        </button>
      )}
    </div>
  );
}
