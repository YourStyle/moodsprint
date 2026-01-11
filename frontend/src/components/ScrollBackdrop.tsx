'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

export function ScrollBackdrop() {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };

    // Check initial scroll position
    handleScroll();

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div
      className={cn(
        'fixed top-0 left-0 right-0 h-12 z-[9999] pointer-events-none',
        'bg-gradient-to-b from-black/60 to-transparent',
        'backdrop-blur-sm',
        'transition-opacity duration-200',
        isScrolled ? 'opacity-100' : 'opacity-0'
      )}
    />
  );
}
