"use client";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { useEffect, useRef, useState, useMemo } from "react";

const DEFAULT_BEAMS = [
  { color: "#10a37f", angle: -45, delay: 0 },
  { color: "#1a73e8", angle: -30, delay: 2 },
  { color: "#8e44ad", angle: -55, delay: 4 },
];

export function BackgroundBeamsWithCollision({
  className,
  beamCount = 3,
}: {
  className?: string;
  beamCount?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const beams = useMemo(
    () => DEFAULT_BEAMS.slice(0, isMobile ? Math.min(beamCount, 2) : beamCount),
    [beamCount, isMobile]
  );

  return (
    <div
      ref={containerRef}
      className={cn("absolute inset-0 overflow-hidden", className)}
    >
      {beams.map((beam, i) => (
        <motion.div
          key={i}
          className="absolute"
          style={{
            height: 2,
            width: "150%",
            left: "-25%",
            top: `${20 + i * 25}%`,
            background: `linear-gradient(90deg, transparent, ${beam.color}80, transparent)`,
            transform: `rotate(${beam.angle}deg)`,
            opacity: isMobile ? 0.3 : 0.5,
          }}
          animate={{
            translateX: ["-30%", "30%", "-30%"],
          }}
          transition={{
            duration: 8 + i * 2,
            repeat: Infinity,
            ease: "easeInOut",
            delay: beam.delay,
          }}
        />
      ))}
      {/* Sparkle collision effects */}
      {beams.map((beam, i) => (
        <Sparkle key={`sparkle-${i}`} color={beam.color} delay={beam.delay + 3} />
      ))}
    </div>
  );
}

function Sparkle({ color, delay }: { color: string; delay: number }) {
  const [pos] = useState(() => ({
    x: Math.random() * 80 + 10,
    y: Math.random() * 60 + 20,
  }));

  return (
    <motion.div
      className="absolute w-1 h-1 rounded-full"
      style={{
        left: `${pos.x}%`,
        top: `${pos.y}%`,
        backgroundColor: color,
        boxShadow: `0 0 6px ${color}`,
      }}
      animate={{
        opacity: [0, 1, 0],
        scale: [0, 1.5, 0],
      }}
      transition={{
        duration: 0.6,
        repeat: Infinity,
        repeatDelay: 4 + Math.random() * 3,
        delay,
      }}
    />
  );
}
