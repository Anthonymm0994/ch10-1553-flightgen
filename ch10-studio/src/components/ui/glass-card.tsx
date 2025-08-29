import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
}

export function GlassCard({ children, className = '' }: GlassCardProps) {
  return (
    <div className={`
      relative overflow-hidden
      bg-white/5 backdrop-blur-xl
      border border-white/10
      rounded-2xl
      shadow-2xl shadow-black/20
      transition-all duration-300
      hover:bg-white/[0.07]
      hover:border-white/20
      hover:shadow-2xl hover:shadow-blue-500/10
      ${className}
    `}>
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 opacity-50" />
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}
