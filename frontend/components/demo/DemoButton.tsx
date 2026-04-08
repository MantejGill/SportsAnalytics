"use client";

import React from "react";
import { motion } from "framer-motion";
import { Play, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";

interface DemoButtonProps {
  onStart: () => void;
  tourWasInterrupted?: boolean;
}

export default function DemoButton({ onStart, tourWasInterrupted }: DemoButtonProps) {
  return (
    <motion.button
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onStart}
      className={cn(
        "fixed bottom-6 left-6 z-[999] flex items-center gap-2 rounded-full px-5 py-3",
        "bg-gradient-to-r from-[#635BFF] to-[#00D4FF] text-white text-sm font-semibold",
        "shadow-lg shadow-[#635BFF]/25 transition-shadow hover:shadow-xl hover:shadow-[#635BFF]/30"
      )}
    >
      {tourWasInterrupted ? (
        <>
          <RotateCcw className="h-4 w-4" />
          Resume Tour
        </>
      ) : (
        <>
          <Play className="h-4 w-4" />
          Start Demo Tour
        </>
      )}
    </motion.button>
  );
}
