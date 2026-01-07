'use client';

import { useState, useEffect, useCallback, ReactNode } from 'react';
import { X, ChevronRight, ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { hapticFeedback } from '@/lib/telegram';
import { useLanguage } from '@/lib/i18n';

export interface OnboardingStep {
  id: string;
  targetSelector: string;
  title: string;
  description: string;
  position?: 'top' | 'bottom' | 'left' | 'right';
}

interface SpotlightOnboardingProps {
  steps: OnboardingStep[];
  storageKey: string;
  onComplete?: () => void;
  children: ReactNode;
}

interface TargetRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export function SpotlightOnboarding({
  steps,
  storageKey,
  onComplete,
  children,
}: SpotlightOnboardingProps) {
  const [currentStep, setCurrentStep] = useState(-1);
  const [targetRect, setTargetRect] = useState<TargetRect | null>(null);
  const [isCompleted, setIsCompleted] = useState(true);
  const { t } = useLanguage();

  // Check if onboarding was already completed
  useEffect(() => {
    const completed = localStorage.getItem(`onboarding_${storageKey}`);
    if (!completed && steps.length > 0) {
      // Delay start to let page render
      const timer = setTimeout(() => {
        setIsCompleted(false);
        setCurrentStep(0);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [storageKey, steps.length]);

  // Update target element position
  useEffect(() => {
    if (currentStep < 0 || currentStep >= steps.length) {
      setTargetRect(null);
      return;
    }

    const step = steps[currentStep];
    const updatePosition = () => {
      const element = document.querySelector(step.targetSelector);
      if (element) {
        const rect = element.getBoundingClientRect();
        setTargetRect({
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
        });
      }
    };

    updatePosition();
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition);

    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition);
    };
  }, [currentStep, steps]);

  const handleNext = useCallback(() => {
    hapticFeedback('light');
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      // Complete onboarding
      localStorage.setItem(`onboarding_${storageKey}`, 'true');
      setIsCompleted(true);
      setCurrentStep(-1);
      onComplete?.();
    }
  }, [currentStep, steps.length, storageKey, onComplete]);

  const handlePrev = useCallback(() => {
    hapticFeedback('light');
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  }, [currentStep]);

  const handleSkip = useCallback(() => {
    hapticFeedback('light');
    localStorage.setItem(`onboarding_${storageKey}`, 'true');
    setIsCompleted(true);
    setCurrentStep(-1);
    onComplete?.();
  }, [storageKey, onComplete]);

  if (isCompleted || currentStep < 0 || !targetRect) {
    return <>{children}</>;
  }

  const step = steps[currentStep];
  const padding = 8;
  const tooltipWidth = 288; // w-72 = 18rem = 288px
  const screenPadding = 16;

  // Calculate tooltip position with boundary checks
  const tooltipPosition = step.position || 'bottom';
  let tooltipStyle: React.CSSProperties = {};

  // Calculate horizontal center of target
  const targetCenterX = targetRect.left + targetRect.width / 2;

  // Check if tooltip would go off-screen when centered
  const wouldOverflowRight = targetCenterX + tooltipWidth / 2 > window.innerWidth - screenPadding;
  const wouldOverflowLeft = targetCenterX - tooltipWidth / 2 < screenPadding;

  switch (tooltipPosition) {
    case 'top':
      tooltipStyle = {
        bottom: `calc(100% - ${targetRect.top - padding - 10}px)`,
      };
      break;
    case 'bottom':
      tooltipStyle = {
        top: targetRect.top + targetRect.height + padding + 10,
      };
      break;
    case 'left':
      tooltipStyle = {
        top: targetRect.top + targetRect.height / 2,
        right: `calc(100% - ${targetRect.left - padding - 10}px)`,
        transform: 'translateY(-50%)',
      };
      break;
    case 'right':
      tooltipStyle = {
        top: targetRect.top + targetRect.height / 2,
        left: targetRect.left + targetRect.width + padding + 10,
        transform: 'translateY(-50%)',
      };
      break;
  }

  // For top/bottom positions, handle horizontal alignment
  if (tooltipPosition === 'top' || tooltipPosition === 'bottom') {
    if (wouldOverflowRight) {
      // Align to right edge of screen
      tooltipStyle.right = screenPadding;
    } else if (wouldOverflowLeft) {
      // Align to left edge of screen
      tooltipStyle.left = screenPadding;
    } else {
      // Center on target
      tooltipStyle.left = targetCenterX;
      tooltipStyle.transform = 'translateX(-50%)';
    }
  }

  return (
    <>
      {children}

      {/* Overlay */}
      <div className="fixed inset-0 z-[9998]" onClick={handleNext}>
        {/* Darkened background with spotlight cutout */}
        <svg className="absolute inset-0 w-full h-full">
          <defs>
            <mask id="spotlight-mask">
              <rect width="100%" height="100%" fill="white" />
              <rect
                x={targetRect.left - padding}
                y={targetRect.top - padding}
                width={targetRect.width + padding * 2}
                height={targetRect.height + padding * 2}
                rx="12"
                fill="black"
              />
            </mask>
          </defs>
          <rect
            width="100%"
            height="100%"
            fill="rgba(0, 0, 0, 0.75)"
            mask="url(#spotlight-mask)"
          />
        </svg>

        {/* Spotlight border */}
        <div
          className="absolute border-2 border-purple-500 rounded-xl pointer-events-none animate-pulse"
          style={{
            top: targetRect.top - padding,
            left: targetRect.left - padding,
            width: targetRect.width + padding * 2,
            height: targetRect.height + padding * 2,
          }}
        />
      </div>

      {/* Tooltip */}
      <div
        className="fixed z-[9999] w-72 bg-gray-800 border border-gray-700 rounded-xl p-4 shadow-xl"
        style={tooltipStyle}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={handleSkip}
          className="absolute top-2 right-2 text-gray-500 hover:text-gray-300 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Content */}
        <h3 className="text-white font-semibold mb-2 pr-6">{step.title}</h3>
        <p className="text-sm text-gray-400 mb-4">{step.description}</p>

        {/* Progress and navigation */}
        <div className="flex items-center justify-between">
          <div className="flex gap-1">
            {steps.map((_, i) => (
              <div
                key={i}
                className={cn(
                  'w-2 h-2 rounded-full transition-colors',
                  i === currentStep ? 'bg-purple-500' : 'bg-gray-600'
                )}
              />
            ))}
          </div>

          <div className="flex gap-2">
            {currentStep > 0 && (
              <Button size="sm" variant="secondary" onClick={handlePrev}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
            )}
            <Button size="sm" onClick={handleNext}>
              {currentStep < steps.length - 1 ? (
                <>
                  {t('spotlightNext')}
                  <ChevronRight className="w-4 h-4 ml-1" />
                </>
              ) : (
                t('spotlightDone')
              )}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}

// Reset onboarding for testing
export function resetOnboarding(storageKey: string) {
  localStorage.removeItem(`onboarding_${storageKey}`);
}
