import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

interface PortalDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  triggerRef: React.RefObject<HTMLElement>;
  children: React.ReactNode;
  className?: string;
}

export const PortalDropdown: React.FC<PortalDropdownProps> = ({
  isOpen,
  onClose,
  triggerRef,
  children,
  className = '',
}) => {
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  const dropdownRef = useRef<HTMLDivElement>(null);

  const updatePosition = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const scrollX = window.scrollX;
      const scrollY = window.scrollY;

      // Position the dropdown below the trigger, aligned to the right
      // We'll adjust logic inside the effect to handle edge cases if needed
      // but simplistic "below-right" is usually a good start.
      // However, the original CSS was absolute right:0, top: 100%.
      // So we want the right edge of dropdown to align with right edge of trigger.

      setPosition({
        top: rect.bottom + scrollY + 5, // 5px gap
        left: rect.right + scrollX, // We will offset by width in CSS/style or calculation
        width: rect.width,
      });
    }
  };

  useEffect(() => {
    if (isOpen) {
      updatePosition();
      // Update position on scroll/resize
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
      // Click outside listener
      const handleClickOutside = (event: MouseEvent) => {
        if (
          dropdownRef.current &&
          !dropdownRef.current.contains(event.target as Node) &&
          triggerRef.current &&
          !triggerRef.current.contains(event.target as Node)
        ) {
          onClose();
        }
      };
      document.addEventListener('mousedown', handleClickOutside);

      return () => {
        window.removeEventListener('scroll', updatePosition, true);
        window.removeEventListener('resize', updatePosition);
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen, onClose, triggerRef]);

  if (!isOpen) return null;

  return createPortal(
    <div
      ref={dropdownRef}
      className={`user-actions-dropdown ${className}`}
      style={{
        position: 'absolute',
        top: position.top,
        left: position.left,
        transform: 'translateX(-100%)', // Align right edge
        minWidth: '180px',
        zIndex: 9999,
        // Override any existing styles that might conflict
        marginTop: 0,
        marginRight: 0,
      }}
    >
      {children}
    </div>,
    document.body
  );
};
