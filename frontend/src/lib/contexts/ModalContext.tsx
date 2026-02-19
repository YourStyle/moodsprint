'use client';

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';

interface ModalContextValue {
  /** True when at least one modal/sheet is open */
  isAnyModalOpen: boolean;
  /** Register an open modal. Returns an unregister function. */
  register: () => () => void;
}

const ModalContext = createContext<ModalContextValue>({
  isAnyModalOpen: false,
  register: () => () => {},
});

export function ModalProvider({ children }: { children: ReactNode }) {
  const countRef = useRef(0);
  const [isAnyModalOpen, setIsAnyModalOpen] = useState(false);

  const register = useCallback(() => {
    countRef.current += 1;
    setIsAnyModalOpen(true);

    return () => {
      countRef.current -= 1;
      if (countRef.current <= 0) {
        countRef.current = 0;
        setIsAnyModalOpen(false);
      }
    };
  }, []);

  return (
    <ModalContext.Provider value={{ isAnyModalOpen, register }}>
      {children}
    </ModalContext.Provider>
  );
}

export function useModalContext() {
  return useContext(ModalContext);
}

/**
 * Hook for components that act as modals/overlays.
 * Registers with ModalContext while `isOpen` is true,
 * so notifications can pause while any modal is visible.
 */
export function useRegisterModal(isOpen: boolean) {
  const { register } = useModalContext();

  useEffect(() => {
    if (!isOpen) return;
    const unregister = register();
    return unregister;
  }, [isOpen, register]);
}
