import { useEffect } from 'react';
import { useAppStore } from '../../store/app.js';
import { OnboardingChecklist } from './OnboardingChecklist.js';
import { TourSpotlight } from './TourSpotlight.js';

// First-time visitors get the welcome tour automatically. After it has been
// offered once (completed OR skipped) we never auto-launch it again — the
// help menu and checklist are the only way back in. This avoids the
// "tutorial reappears every reload" frustration when a user dismisses it.
export function TourProvider() {
  const toursCompleted = useAppStore((s) => s.toursCompleted);
  const toursSeen = useAppStore((s) => s.toursSeen);
  const activeTour = useAppStore((s) => s.activeTour);
  const startTour = useAppStore((s) => s.startTour);

  useEffect(() => {
    if (toursCompleted.includes('welcome') || toursSeen.includes('welcome')) return;
    if (activeTour) return;
    // Delay so layout has time to settle and target elements exist before
    // the spotlight tries to measure them.
    const timer = setTimeout(() => {
      const s = useAppStore.getState();
      if (s.activeTour) return;
      if (s.toursCompleted.includes('welcome') || s.toursSeen.includes('welcome')) return;
      startTour('welcome');
    }, 800);
    return () => clearTimeout(timer);
  }, [toursCompleted, toursSeen, activeTour, startTour]);

  return (
    <>
      <TourSpotlight />
      <OnboardingChecklist />
    </>
  );
}
