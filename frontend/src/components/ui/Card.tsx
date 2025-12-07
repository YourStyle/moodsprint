'use client';

import { HTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'gradient' | 'outlined';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'glass', padding = 'md', hover = false, children, ...props }, ref) => {
    const variants = {
      default: 'bg-dark-700/60 border border-purple-500/10',
      glass: 'glass-card',
      gradient: 'bg-gradient-to-br from-purple-500/20 to-blue-500/10 border border-purple-500/20 backdrop-blur-xl',
      outlined: 'bg-transparent border border-purple-500/20',
    };

    const paddings = {
      none: '',
      sm: 'p-3',
      md: 'p-4',
      lg: 'p-6',
    };

    const hoverStyles = hover
      ? 'hover:border-purple-500/30 hover:shadow-glow transition-all cursor-pointer'
      : '';

    return (
      <div
        ref={ref}
        className={clsx(
          'rounded-2xl',
          variants[variant],
          paddings[padding],
          hoverStyles,
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';
