"use client";

import { motion, type Variants } from "framer-motion";
import type { ReactNode } from "react";

const EASE = [0.22, 1, 0.36, 1] as const;

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.02 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: EASE } },
};

interface MotionProps {
  children: ReactNode;
  className?: string;
}

/** Fades and slides a single block in on mount. */
export function FadeIn({ children, className, delay = 0 }: MotionProps & { delay?: number }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}

/** Staggers the entrance of its <StaggerItem> children. */
export function Stagger({ children, className }: MotionProps) {
  return (
    <motion.div className={className} variants={container} initial="hidden" animate="show">
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: MotionProps) {
  return (
    <motion.div className={className} variants={item}>
      {children}
    </motion.div>
  );
}
