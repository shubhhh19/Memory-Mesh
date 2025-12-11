'use client';

import { motion } from 'framer-motion';
import { Icon } from '@iconify/react';

interface ComingSoonOverlayProps {
  feature: string;
  description?: string;
}

export default function ComingSoonOverlay({ 
  feature, 
  description = 'This feature requires backend connection'
}: ComingSoonOverlayProps) {
  return (
    <div className="relative w-full min-h-[500px] rounded-2xl border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.55)] backdrop-blur-xl overflow-hidden">
      {/* Animated Background Pattern */}
      <div className="absolute inset-0 opacity-[0.03]">
        <div 
          className="absolute inset-0"
          style={{
            backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, currentColor 10px, currentColor 20px)',
            color: 'var(--accent)'
          }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-[500px] p-8 text-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="mb-6"
        >
          <div className="relative w-24 h-24 mx-auto">
            {/* Pulsing Icon */}
            <motion.div
              animate={{ 
                scale: [1, 1.15, 1],
                rotate: [0, 5, -5, 0]
              }}
              transition={{ 
                duration: 2.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
              className="w-24 h-24 rounded-full bg-gradient-to-br from-[var(--accent)] via-blue-500 to-purple-500 flex items-center justify-center border-4 border-[var(--border)] shadow-xl"
            >
              <Icon icon="material-symbols:construction" className="w-12 h-12 text-white" />
            </motion.div>
            
            {/* Orbiting Dots */}
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="absolute top-1/2 left-1/2 w-3 h-3 rounded-full bg-[var(--accent)]"
                style={{
                  transformOrigin: '48px 0',
                }}
                animate={{
                  rotate: [0, 360],
                }}
                transition={{
                  duration: 4 + i * 0.5,
                  repeat: Infinity,
                  ease: "linear",
                  delay: i * 0.4
                }}
              />
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <h3 className="text-3xl font-light text-[var(--text)] mb-3">
            {feature}
          </h3>
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[rgb(var(--accent-rgb)/0.15)] border border-[rgb(var(--accent-rgb)/0.3)] mb-4">
            <Icon icon="material-symbols:schedule" className="w-4 h-4 text-[var(--accent)]" />
            <span className="text-sm font-medium text-[var(--accent)]">Coming Soon</span>
          </div>
        </motion.div>

        <motion.p
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-[var(--muted-text)] max-w-lg mb-8 text-base leading-relaxed"
        >
          {description}
        </motion.p>

        {/* Progress Indicator */}
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: '100%', opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.8 }}
          className="w-full max-w-md"
        >
          <div className="h-2 bg-[rgb(var(--surface-rgb)/0.6)] rounded-full overflow-hidden mb-2">
            <motion.div
              className="h-full bg-gradient-to-r from-[var(--accent)] via-blue-500 to-purple-500"
              initial={{ width: 0 }}
              animate={{ width: ['0%', '60%', '100%', '60%', '0%'] }}
              transition={{ 
                delay: 0.7,
                duration: 3,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          </div>
          <p className="text-xs text-[var(--muted-text)]">Backend integration in progress...</p>
        </motion.div>

        {/* Fun Fact */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-8 p-5 rounded-xl bg-[rgb(var(--surface-rgb)/0.6)] border border-[var(--border)] max-w-lg"
        >
          <div className="flex items-start gap-3">
            <Icon icon="material-symbols:lightbulb" className="w-6 h-6 text-[var(--accent)] flex-shrink-0 mt-0.5" />
            <div className="text-left">
              <p className="text-sm font-medium text-[var(--text)] mb-2">Did you know?</p>
              <p className="text-sm text-[var(--muted-text)] leading-relaxed">
                This feature uses our unique hybrid ranking algorithm that combines vector similarity, importance scoring, and temporal decay—something most vector databases don&apos;t offer!
              </p>
            </div>
          </div>
        </motion.div>

        {/* Call to Action */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 1 }}
          className="mt-8 flex flex-col sm:flex-row gap-3"
        >
          <a
            href="https://github.com/shubhhh19/memory-layer"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.6)] text-[var(--text)] hover:bg-[rgb(var(--surface-rgb)/0.8)] transition-colors text-sm font-medium"
          >
            <Icon icon="mdi:github" className="w-5 h-5" />
            <span>View on GitHub</span>
          </a>
          <a
            href="https://github.com/shubhhh19/memory-layer#readme"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-[var(--accent)] text-[var(--surface)] hover:opacity-90 transition-opacity text-sm font-medium"
          >
            <Icon icon="material-symbols:book" className="w-5 h-5" />
            <span>Read Documentation</span>
          </a>
        </motion.div>
      </div>
    </div>
  );
}

