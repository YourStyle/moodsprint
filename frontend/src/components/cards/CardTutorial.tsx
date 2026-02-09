'use client';

import { useState } from 'react';
import { Layers, Swords, Sparkles, GitMerge } from 'lucide-react';
import { Button, Modal } from '@/components/ui';
import { useLanguage, TranslationKey } from '@/lib/i18n';

const TUTORIAL_STORAGE_KEY = 'card_tutorial_seen';

const STEPS: { iconKey: string; titleKey: TranslationKey; textKey: TranslationKey }[] = [
  { iconKey: 'cards', titleKey: 'tutorialStep1Title', textKey: 'tutorialStep1Text' },
  { iconKey: 'deck', titleKey: 'tutorialStep2Title', textKey: 'tutorialStep2Text' },
  { iconKey: 'battle', titleKey: 'tutorialStep3Title', textKey: 'tutorialStep3Text' },
  { iconKey: 'merge', titleKey: 'tutorialStep4Title', textKey: 'tutorialStep4Text' },
];

const STEP_ICONS: Record<string, React.ReactNode> = {
  cards: <Sparkles className="w-10 h-10 text-yellow-400" />,
  deck: <Layers className="w-10 h-10 text-blue-400" />,
  battle: <Swords className="w-10 h-10 text-red-400" />,
  merge: <GitMerge className="w-10 h-10 text-purple-400" />,
};

const STEP_COLORS = [
  'from-yellow-500/20 to-amber-500/20',
  'from-blue-500/20 to-cyan-500/20',
  'from-red-500/20 to-orange-500/20',
  'from-purple-500/20 to-pink-500/20',
];

interface CardTutorialProps {
  isOpen: boolean;
  onClose: () => void;
}

export function shouldShowCardTutorial(): boolean {
  if (typeof window === 'undefined') return false;
  return !localStorage.getItem(TUTORIAL_STORAGE_KEY);
}

export function markCardTutorialSeen(): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TUTORIAL_STORAGE_KEY, 'true');
}

export function CardTutorial({ isOpen, onClose }: CardTutorialProps) {
  const { t } = useLanguage();
  const [step, setStep] = useState(0);

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      markCardTutorialSeen();
      setStep(0);
      onClose();
    }
  };

  const handleClose = () => {
    markCardTutorialSeen();
    setStep(0);
    onClose();
  };

  const currentStep = STEPS[step];

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={t('tutorialTitle')}>
      <div className="flex flex-col items-center">
        {/* Step icon */}
        <div className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${STEP_COLORS[step]} flex items-center justify-center mb-4`}>
          {STEP_ICONS[currentStep.iconKey]}
        </div>

        {/* Step content */}
        <h3 className="text-lg font-bold text-white mb-2">
          {t(currentStep.titleKey)}
        </h3>
        <p className="text-gray-400 text-sm text-center mb-6 leading-relaxed">
          {t(currentStep.textKey)}
        </p>

        {/* Step indicators */}
        <div className="flex gap-2 mb-4">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`w-2 h-2 rounded-full transition-all ${
                i === step ? 'bg-purple-500 w-6' : 'bg-gray-600'
              }`}
            />
          ))}
        </div>

        {/* Action button */}
        <Button onClick={handleNext} className="w-full">
          {step < STEPS.length - 1 ? t('next') : t('tutorialGotIt')}
        </Button>
      </div>
    </Modal>
  );
}
