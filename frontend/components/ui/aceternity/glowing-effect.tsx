"use client";
import { cn } from "@/lib/utils";
import { useRef, useCallback, useEffect, useState } from "react";

export function GlowingEffect({
  children,
  className,
  containerClassName,
  glowColor = "rgba(99, 91, 255, 0.15)",
  glowSize = 600,
  disabled = false,
}: {
  children: React.ReactNode;
  className?: string;
  containerClassName?: string;
  glowColor?: string;
  glowSize?: number;
  disabled?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [glowStyle, setGlowStyle] = useState<React.CSSProperties>({});
  const [isHovering, setIsHovering] = useState(false);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (disabled || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Calculate angle for conic gradient
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const angle = Math.atan2(y - centerY, x - centerX) * (180 / Math.PI) + 90;

      setGlowStyle({
        background: `
          radial-gradient(${glowSize}px circle at ${x}px ${y}px, ${glowColor}, transparent 40%),
          conic-gradient(from ${angle}deg at ${x}px ${y}px, ${glowColor}, transparent 60%)
        `,
        opacity: 1,
        transition: "opacity 0.3s ease",
      });
    },
    [disabled, glowColor, glowSize]
  );

  const handleMouseEnter = useCallback(() => {
    if (!disabled) setIsHovering(true);
  }, [disabled]);

  const handleMouseLeave = useCallback(() => {
    setIsHovering(false);
    setGlowStyle((prev) => ({ ...prev, opacity: 0 }));
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    el.addEventListener("mousemove", handleMouseMove);
    el.addEventListener("mouseenter", handleMouseEnter);
    el.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      el.removeEventListener("mousemove", handleMouseMove);
      el.removeEventListener("mouseenter", handleMouseEnter);
      el.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [handleMouseMove, handleMouseEnter, handleMouseLeave]);

  return (
    <div
      ref={containerRef}
      className={cn("relative", containerClassName)}
    >
      {/* Glow layer */}
      <div
        className={cn(
          "absolute inset-0 pointer-events-none rounded-[inherit] z-0",
          !isHovering && "opacity-0"
        )}
        style={{
          ...glowStyle,
          borderRadius: "inherit",
        }}
      />
      {/* Content */}
      <div className={cn("relative z-10 w-full h-full", className)}>{children}</div>
    </div>
  );
}
