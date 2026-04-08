"use client";
import { cn } from "@/lib/utils";
import { motion, stagger, useAnimate, useInView } from "framer-motion";
import { useEffect } from "react";

export function TextGenerateEffect({
  words,
  className,
  filter = true,
  duration = 0.5,
  textClassName = "text-gray-900 dark:text-gray-100",
}: {
  words: string;
  className?: string;
  filter?: boolean;
  duration?: number;
  textClassName?: string;
}) {
  const [scope, animate] = useAnimate();
  const isInView = useInView(scope, { once: true });
  const wordsArray = words.split(" ");

  useEffect(() => {
    if (isInView) {
      animate(
        "span",
        { opacity: 1, filter: filter ? "blur(0px)" : "none" },
        { duration, delay: stagger(0.1) }
      );
    }
  }, [isInView, animate, filter, duration, words]);

  return (
    <div className={cn("font-medium", className)} ref={scope}>
      <div className="leading-snug">
        {wordsArray.map((word, idx) => (
          <motion.span
            key={word + idx}
            className={cn(textClassName, "inline-block mr-[0.25em]")}
            style={{
              opacity: 0,
              filter: filter ? "blur(10px)" : "none",
            }}
          >
            {word}
          </motion.span>
        ))}
      </div>
    </div>
  );
}
