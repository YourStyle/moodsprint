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
  const scrollYRef = useRef(0);

  // Lock body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      scrollYRef.current = window.scrollY;
      document.body.classList.add('modal-open');
      document.body.style.top = `-${scrollYRef.current}px`;
    } else {
      document.body.classList.remove('modal-open');
      document.body.style.top = '';
      window.scrollTo(0, scrollYRef.current);
    }

    return () => {
      document.body.classList.remove('modal-open');
      document.body.style.top = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-end justify-center">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Modal content */}
      <div
        ref={modalRef}
        className={clsx(
          'relative w-full glass-strong animate-slide-up overflow-y-auto',
          fullScreen
            ? 'h-full rounded-none'
            : 'rounded-t-3xl max-h-[80vh] mt-16',
          'p-6 pb-8',
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
                className="p-2 -mr-2 text-gray-400 hover:text-white rounded-full hover:bg-purple-500/20 transition-colors ml-auto"
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
