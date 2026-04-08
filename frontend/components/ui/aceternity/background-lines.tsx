"use client";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

export function BackgroundLines({
  children,
  className,
  lineColor = "rgba(99, 91, 255, 0.04)",
  lineCount = 6,
  animationDuration = 8,
}: {
  children?: React.ReactNode;
  className?: string;
  lineColor?: string;
  lineCount?: number;
  animationDuration?: number;
}) {
  return (
    <div className={cn("relative overflow-hidden", className)}>
      {/* Animated diagonal lines */}
      <div className="pointer-events-none absolute inset-0 z-0">
        {Array.from({ length: lineCount }).map((_, i) => {
          const offset = (i / lineCount) * 100;
          const delay = (i / lineCount) * animationDuration;
          return (
            <motion.div
              key={i}
              className="absolute h-[200%] w-px"
              style={{
                left: `${offset}%`,
                top: "-50%",
                background: `linear-gradient(180deg, transparent 0%, ${lineColor} 30%, ${lineColor} 70%, transparent 100%)`,
                transform: "rotate(15deg)",
                transformOrigin: "center center",
              }}
              animate={{
                y: ["-10%", "10%"],
              }}
              transition={{
                duration: animationDuration,
                delay,
                repeat: Infinity,
                repeatType: "reverse",
                ease: "easeInOut",
              }}
            />
          );
        })}
      </div>
      {/* Content */}
      <div className="relative z-10">{children}</div>
    </div>
  );
}
