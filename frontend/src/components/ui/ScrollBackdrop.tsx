'use client';

import { useState, useEffect } from 'react';

export function ScrollBackdrop() {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div
      className={`fixed top-0 left-0 right-0 h-[60px] backdrop-blur-xl bg-gradient-to-b from-dark-900 to-dark-900/50 z-40 pointer-events-none transition-opacity duration-200 ${isScrolled ? 'opacity-100' : 'opacity-0'}`}
    />
  );
}
