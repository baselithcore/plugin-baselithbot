import React from 'react';
import type { BotDetectionSignals } from '../types';
import './BotIndicator.css';

interface BotIndicatorProps {
  isBot: boolean | null;
  confidence: number | null;
  signals?: BotDetectionSignals | null;
  size?: 'small' | 'medium' | 'large';
  showLabel?: boolean;
}

/**
 * Modern visual indicator showing if an attack was from a bot or human.
 * Features custom SVG icons with subtle animations and glow effects.
 */
const BotIndicator: React.FC<BotIndicatorProps> = ({
  isBot,
  confidence,
  signals,
  size = 'medium',
  showLabel = true,
}) => {
  // Determine classification based on is_bot and confidence
  const getClassification = (): 'bot' | 'human' | 'unknown' => {
    if (isBot === null || confidence === null) return 'unknown';
    if (isBot) return 'bot';
    if (confidence <= 0.25) return 'human';
    return 'unknown';
  };

  const classification = getClassification();

  const iconSizes = {
    small: 14,
    medium: 18,
    large: 26,
  };

  const iconSize = iconSizes[size];

  const getTooltipContent = (): string => {
    if (confidence === null) return 'Not analyzed';

    const pct = Math.round(confidence * 100);

    // Context-aware prefix
    let prefix = '';
    if (classification === 'human') {
      prefix = 'Likely Human';
    } else if (classification === 'bot') {
      prefix = 'Bot Detected';
    } else {
      prefix = 'Analysis Unknown';
    }

    let tooltip = `${prefix} (${pct}% bot confidence)`;

    if (signals) {
      const parts: string[] = [];
      if (signals.inter_request_interval_ms !== null) {
        parts.push(`Interval: ${signals.inter_request_interval_ms.toFixed(0)}ms`);
      }
      if (signals.request_rate_per_minute !== null) {
        parts.push(`Rate: ${signals.request_rate_per_minute.toFixed(1)}/min`);
      }
      if (signals.timing_variance !== null) {
        parts.push(`Variance: ${signals.timing_variance.toFixed(0)}ms`);
      }
      if (parts.length > 0) {
        tooltip += ` | ${parts.join(', ')}`;
      }
    }

    return tooltip;
  };

  // Modern Bot Icon - Sleek robot head with animated eyes
  const BotIcon = () => (
    <svg
      width={iconSize}
      height={iconSize}
      viewBox="0 0 24 24"
      fill="none"
      className="bi-icon bi-icon--bot"
    >
      {/* Robot head outline */}
      <rect
        x="4"
        y="8"
        width="16"
        height="12"
        rx="3"
        stroke="currentColor"
        strokeWidth="1.8"
        fill="rgba(239, 68, 68, 0.1)"
      />
      {/* Antenna */}
      <path
        d="M12 8V5M12 5L10 3M12 5L14 3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      {/* Eyes - animated */}
      <circle cx="9" cy="13" r="2" fill="currentColor" className="bi-bot-eye bi-bot-eye--left" />
      <circle cx="15" cy="13" r="2" fill="currentColor" className="bi-bot-eye bi-bot-eye--right" />
      {/* Mouth grid */}
      <rect x="8" y="16" width="8" height="2" rx="1" fill="currentColor" opacity="0.6" />
    </svg>
  );

  // Modern Human Icon - Stylized person silhouette with verification
  const HumanIcon = () => (
    <svg
      width={iconSize}
      height={iconSize}
      viewBox="0 0 24 24"
      fill="none"
      className="bi-icon bi-icon--human"
    >
      {/* Head */}
      <circle
        cx="12"
        cy="8"
        r="4"
        stroke="currentColor"
        strokeWidth="1.8"
        fill="rgba(34, 197, 94, 0.1)"
      />
      {/* Body */}
      <path
        d="M6 21V19C6 16.2386 8.23858 14 11 14H13C15.7614 14 18 16.2386 18 19V21"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="rgba(34, 197, 94, 0.05)"
      />
      {/* Verification badge */}
      <circle cx="17" cy="17" r="4" fill="#22c55e" className="bi-human-badge" />
      <path
        d="M15.5 17L16.5 18L18.5 16"
        stroke="white"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );

  // Unknown/Scanning Icon - Question mark with scanning animation
  const UnknownIcon = () => (
    <svg
      width={iconSize}
      height={iconSize}
      viewBox="0 0 24 24"
      fill="none"
      className="bi-icon bi-icon--unknown"
    >
      {/* Outer scanning ring */}
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeDasharray="4 2"
        opacity="0.4"
        className="bi-scan-ring"
      />
      {/* Inner circle */}
      <circle
        cx="12"
        cy="12"
        r="6"
        stroke="currentColor"
        strokeWidth="1.8"
        fill="rgba(156, 163, 175, 0.1)"
      />
      {/* Question mark */}
      <text
        x="12"
        y="16"
        textAnchor="middle"
        fill="currentColor"
        fontSize="10"
        fontWeight="bold"
        fontFamily="system-ui"
      >
        ?
      </text>
    </svg>
  );

  const renderIcon = () => {
    switch (classification) {
      case 'bot':
        return <BotIcon />;
      case 'human':
        return <HumanIcon />;
      default:
        return <UnknownIcon />;
    }
  };

  const renderLabel = () => {
    if (!showLabel) return null;

    switch (classification) {
      case 'bot':
        return <span className="bi-label bi-label--bot">BOT</span>;
      case 'human':
        return <span className="bi-label bi-label--human">HUMAN</span>;
      default:
        return <span className="bi-label bi-label--unknown">?</span>;
    }
  };

  return (
    <div
      className={`bot-indicator bot-indicator--${size} bot-indicator--${classification}`}
      title={getTooltipContent()}
    >
      {renderIcon()}
      {renderLabel()}
      {confidence !== null && size !== 'small' && (
        <span className="bi-confidence">{Math.round(confidence * 100)}%</span>
      )}
    </div>
  );
};

export default BotIndicator;
