'use client';

import { ReactNode, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import clsx from 'clsx';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  showClose?: boolean;
  className?: string;
  fullScreen?: boolean;
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  showClose = true,
  className,
  fullScreen = false,
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Handle keyboard appearance on mobile
  useEffect(() => {
    if (!isOpen) return;

    const handleResize = () => {
      if (modalRef.current && window.visualViewport) {
        const viewport = window.visualViewport;
        modalRef.current.style.maxHeight = `${viewport.height - 20}px`;
      }
    };

    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', handleResize);
      handleResize();
    }

    return () => {
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', handleResize);
      }
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        ref={modalRef}
        className={clsx(
          'relative w-full glass-strong animate-slide-up overflow-y-auto',
          fullScreen
            ? 'h-full rounded-none'
            : 'sm:w-auto sm:min-w-[320px] sm:max-w-md rounded-t-3xl sm:rounded-2xl max-h-[85vh]',
          'p-6 pb-safe',
          className
        )}
      >
        {(title || showClose) && (
          <div className="flex items-center justify-between mb-4">
            {title && (
              <h2 className="text-xl font-semibold text-white">{title}</h2>
            )}
            {showClose && (
              <button
                onClick={onClose}
                className="p-2 -mr-2 text-gray-400 hover:text-white rounded-full hover:bg-purple-500/20 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
