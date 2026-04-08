"use client";
import { cn } from "@/lib/utils";
import {
  motion,
  useAnimationFrame,
  useMotionTemplate,
  useMotionValue,
  useTransform,
} from "framer-motion";
import { useRef } from "react";

export function MovingBorder({
  children,
  duration = 3000,
  className,
  containerClassName,
  borderClassName,
  as: Component = "div",
  ...otherProps
}: {
  children: React.ReactNode;
  duration?: number;
  className?: string;
  containerClassName?: string;
  borderClassName?: string;
  as?: React.ElementType;
  [key: string]: unknown;
}) {
  return (
    <Component
      className={cn("relative overflow-hidden p-[1px] rounded-2xl", containerClassName)}
      {...otherProps}
    >
      <div className="absolute inset-0" style={{ borderRadius: "inherit" }}>
        <MovingBorderGlow duration={duration} className={borderClassName} />
      </div>
      <div
        className={cn("relative z-10 w-full h-full", className)}
        style={{ borderRadius: "inherit" }}
      >
        {children}
      </div>
    </Component>
  );
}

function MovingBorderGlow({
  duration = 3000,
  className,
}: {
  duration?: number;
  className?: string;
}) {
  const pathRef = useRef<SVGRectElement>(null);
  const progress = useMotionValue(0);

  useAnimationFrame((time) => {
    const length = pathRef.current?.getTotalLength();
    if (length) {
      const pxPerMs = length / duration;
      progress.set((time * pxPerMs) % length);
    }
  });

  const x = useTransform(progress, (val) => pathRef.current?.getPointAtLength(val)?.x ?? 0);
  const y = useTransform(progress, (val) => pathRef.current?.getPointAtLength(val)?.y ?? 0);
  const transform = useMotionTemplate`translateX(${x}px) translateY(${y}px) translateX(-50%) translateY(-50%)`;

  return (
    <>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
        className="absolute h-full w-full"
        width="100%"
        height="100%"
      >
        <rect
          fill="none"
          width="100%"
          height="100%"
          rx="16"
          ry="16"
          ref={pathRef}
        />
      </svg>
      <motion.div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          display: "inline-block",
          transform,
        }}
      >
        <div
          className={cn(
            "h-20 w-20 opacity-[0.8]",
            "bg-[radial-gradient(rgba(99,91,255,0.8)_40%,transparent_60%)]",
            className
          )}
        />
      </motion.div>
    </>
  );
}
