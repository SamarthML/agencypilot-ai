"use client";

import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "framer-motion";
import { useEffect } from "react";

import { SCORE_BAND_LABEL, scoreBand, type ScoreBand } from "@/lib/seo";
import { cn } from "@/lib/utils";

const SIZE = 168;
const STROKE = 12;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const BAND_STROKE: Record<ScoreBand, string> = {
  poor: "stroke-destructive",
  fair: "stroke-warning",
  good: "stroke-success",
};
const BAND_TEXT: Record<ScoreBand, string> = {
  poor: "text-destructive",
  fair: "text-warning",
  good: "text-success",
};

/** Circular 0-100 gauge: red < 50, amber < 80, green ≥ 80. Animates on mount. */
export function ScoreGauge({ score }: { score: number }) {
  const band = scoreBand(score);
  const reduceMotion = useReducedMotion();
  const count = useMotionValue(reduceMotion ? score : 0);
  const rounded = useTransform(count, (value) => Math.round(value));

  useEffect(() => {
    const controls = animate(count, score, { duration: reduceMotion ? 0 : 1.1, ease: "easeOut" });
    return () => controls.stop();
  }, [count, score, reduceMotion]);

  return (
    <div
      className="relative shrink-0"
      style={{ width: SIZE, height: SIZE }}
      role="img"
      aria-label={`SEO score ${score} out of 100 (${SCORE_BAND_LABEL[band]})`}
    >
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} className="-rotate-90">
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          strokeWidth={STROKE}
          className="stroke-muted"
        />
        <motion.circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          className={BAND_STROKE[band]}
          initial={{ strokeDashoffset: reduceMotion ? CIRCUMFERENCE * (1 - score / 100) : CIRCUMFERENCE }}
          animate={{ strokeDashoffset: CIRCUMFERENCE * (1 - score / 100) }}
          transition={{ duration: reduceMotion ? 0 : 1.1, ease: "easeOut" }}
        />
      </svg>
      <div aria-hidden className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span className="text-5xl font-semibold tracking-tight tabular-nums">{rounded}</motion.span>
        <span className={cn("text-xs font-medium", BAND_TEXT[band])}>{SCORE_BAND_LABEL[band]}</span>
      </div>
    </div>
  );
}
