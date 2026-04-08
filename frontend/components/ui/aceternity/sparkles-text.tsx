"use client";
import { cn } from "@/lib/utils";
import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState, useCallback, useRef } from "react";

interface Sparkle {
  id: string;
  x: string;
  y: string;
  color: string;
  delay: number;
  scale: number;
}

const DEFAULT_COLORS = ["#4B5AF0", "#0099CC", "#6B75E0"];

function generateSparkle(colors: string[]): Sparkle {
  return {
    id: Math.random().toString(36).slice(2),
    x: `${Math.random() * 100}%`,
    y: `${Math.random() * 100}%`,
    color: colors[Math.floor(Math.random() * colors.length)],
    delay: Math.random() * 2,
    scale: Math.random() * 0.5 + 0.5,
  };
}

function SparkleIcon({ color, size }: { color: string; size: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M12 0L14.59 8.41L23 12L14.59 15.59L12 24L9.41 15.59L1 12L9.41 8.41L12 0Z"
        fill={color}
      />
    </svg>
  );
}

export function SparklesText({
  children,
  className,
  sparklesCount = 5,
  colors = DEFAULT_COLORS,
}: {
  children: React.ReactNode;
  className?: string;
  sparklesCount?: number;
  colors?: string[];
}) {
  const prefersReducedMotion = useReducedMotion();
  const [sparkles, setSparkles] = useState<Sparkle[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  const updateSparkles = useCallback(() => {
    setSparkles(Array.from({ length: sparklesCount }, () => generateSparkle(colors)));
  }, [sparklesCount, colors]);

  useEffect(() => {
    if (prefersReducedMotion) return;
    updateSparkles();
    intervalRef.current = setInterval(updateSparkles, 3000);
    return () => clearInterval(intervalRef.current);
  }, [updateSparkles, prefersReducedMotion]);

  if (prefersReducedMotion) {
    return <span className={className}>{children}</span>;
  }

  return (
    <span className={cn("relative inline-block", className)}>
      {sparkles.map((sparkle) => (
        <motion.span
          key={sparkle.id}
          className="pointer-events-none absolute z-20"
          style={{
            left: sparkle.x,
            top: sparkle.y,
          }}
          initial={{ opacity: 0, scale: 0 }}
          animate={{
            opacity: [0, 1, 0],
            scale: [0, sparkle.scale, 0],
          }}
          transition={{
            duration: 1.5,
            delay: sparkle.delay,
            ease: "easeInOut",
          }}
        >
          <SparkleIcon color={sparkle.color} size={12} />
        </motion.span>
      ))}
      <span className="relative z-10">{children}</span>
    </span>
  );
}
