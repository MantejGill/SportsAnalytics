"use client";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";

export function AuroraBackground({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return (
    <div
      className={cn(
        "relative overflow-hidden bg-[#faf9f7] dark:bg-[#1a1615]",
        className
      )}
    >
      {/* Aurora gradient layers */}
      <div className="absolute inset-0 mix-blend-soft-light">
        <div
          className="absolute inset-0 animate-aurora-1"
          style={{
            background:
              "radial-gradient(ellipse 80% 50% at 50% 50%, rgba(207, 141, 19, 0.3), transparent 70%)",
          }}
        />
        <div
          className="absolute inset-0 animate-aurora-2"
          style={{
            background:
              "radial-gradient(ellipse 60% 40% at 30% 60%, rgba(110, 123, 255, 0.25), transparent 70%)",
          }}
        />
        {!isMobile && (
          <div
            className="absolute inset-0 animate-aurora-3"
            style={{
              background:
                "radial-gradient(ellipse 50% 60% at 70% 40%, rgba(0, 212, 255, 0.2), transparent 70%)",
            }}
          />
        )}
      </div>
      {/* Content */}
      <div className="relative z-10">{children}</div>

      <style>{`
        @keyframes aurora-1 {
          0%, 100% { transform: translate(0%, 0%) scale(1); }
          33% { transform: translate(5%, -5%) scale(1.1); }
          66% { transform: translate(-3%, 3%) scale(0.95); }
        }
        @keyframes aurora-2 {
          0%, 100% { transform: translate(0%, 0%) scale(1); }
          50% { transform: translate(-8%, 5%) scale(1.15); }
        }
        @keyframes aurora-3 {
          0%, 100% { transform: translate(0%, 0%) rotate(0deg); }
          50% { transform: translate(6%, -4%) rotate(3deg); }
        }
        .animate-aurora-1 { animation: aurora-1 6s ease-in-out infinite; }
        .animate-aurora-2 { animation: aurora-2 8s ease-in-out infinite; }
        .animate-aurora-3 { animation: aurora-3 12s ease-in-out infinite; }
      `}</style>
    </div>
  );
}
