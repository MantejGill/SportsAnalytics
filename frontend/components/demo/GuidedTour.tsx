"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

export interface TourStepAction {
  type: "click" | "fill";
  selector: string;
  value?: string;
}

export interface TourStep {
  target: string;
  title: string;
  description: string;
  placement?: "top" | "bottom" | "left" | "right";
  path?: string;
  waitFor?: number;
  action?: TourStepAction;
  autoAdvanceMs?: number;
}

interface GuidedTourProps {
  steps: TourStep[];
  isActive: boolean;
  onComplete: () => void;
  onSkip: () => void;
}

interface TargetRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const PADDING = 8;
const TOOLTIP_WIDTH = 340;
const TOOLTIP_OFFSET = 16;

function getTooltipPosition(
  rect: TargetRect,
  placement: "top" | "bottom" | "left" | "right",
  tooltipHeight: number
) {
  const scrollX = window.scrollX;
  const scrollY = window.scrollY;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let top = 0;
  let left = 0;

  switch (placement) {
    case "bottom":
      top = rect.top + rect.height + TOOLTIP_OFFSET;
      left = rect.left + rect.width / 2 - TOOLTIP_WIDTH / 2;
      break;
    case "top":
      top = rect.top - tooltipHeight - TOOLTIP_OFFSET;
      left = rect.left + rect.width / 2 - TOOLTIP_WIDTH / 2;
      break;
    case "left":
      top = rect.top + rect.height / 2 - tooltipHeight / 2;
      left = rect.left - TOOLTIP_WIDTH - TOOLTIP_OFFSET;
      break;
    case "right":
      top = rect.top + rect.height / 2 - tooltipHeight / 2;
      left = rect.left + rect.width + TOOLTIP_OFFSET;
      break;
  }

  // Clamp to viewport
  if (left < 12) left = 12;
  if (left + TOOLTIP_WIDTH > vw - 12) left = vw - TOOLTIP_WIDTH - 12;
  if (top < 12) top = 12;
  if (top + tooltipHeight > vh - 12) top = vh - tooltipHeight - 12;

  return { top, left };
}

export default function GuidedTour({
  steps,
  isActive,
  onComplete,
  onSkip,
}: GuidedTourProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [targetRect, setTargetRect] = useState<TargetRect | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const retryRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const step = steps[currentStep];

  const findAndHighlightTarget = useCallback(() => {
    if (!step) return;

    const el = document.querySelector(step.target);
    if (el) {
      retryRef.current = 0;

      // Scroll into view
      el.scrollIntoView({ behavior: "smooth", block: "center" });

      // Small delay after scroll to get correct rect
      setTimeout(() => {
        const rect = el.getBoundingClientRect();
        setTargetRect({
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
        });
        setIsVisible(true);
      }, 300);
    } else if (retryRef.current < 10) {
      retryRef.current += 1;
      timerRef.current = setTimeout(findAndHighlightTarget, 500);
    } else {
      // Element not found after retries, show tooltip in center
      setTargetRect(null);
      setIsVisible(true);
    }
  }, [step]);

  // On step change, find the target
  useEffect(() => {
    if (!isActive) return;

    setIsVisible(false);
    retryRef.current = 0;

    const delay = step?.waitFor || 0;
    timerRef.current = setTimeout(findAndHighlightTarget, delay);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isActive, currentStep, findAndHighlightTarget, step]);

  // Listen for window resize/scroll to update rect
  useEffect(() => {
    if (!isActive || !isVisible) return;

    const updateRect = () => {
      if (!step) return;
      const el = document.querySelector(step.target);
      if (el) {
        const rect = el.getBoundingClientRect();
        setTargetRect({
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
        });
      }
    };

    window.addEventListener("resize", updateRect);
    window.addEventListener("scroll", updateRect, true);
    return () => {
      window.removeEventListener("resize", updateRect);
      window.removeEventListener("scroll", updateRect, true);
    };
  }, [isActive, isVisible, step]);

  // Reset on activate
  useEffect(() => {
    if (isActive) {
      setCurrentStep(0);
      setIsVisible(false);
    }
  }, [isActive]);

  const handleNext = useCallback(() => {
    const step = steps[currentStep];

    // Execute action when leaving this step (clicking Next)
    if (step?.action) {
      const { type, selector, value } = step.action;
      // Try multiple selector strategies
      let el: HTMLElement | null = null;
      // First try direct CSS selector
      try {
        el = document.querySelector(selector) as HTMLElement;
      } catch { /* invalid selector */ }
      // Fallback: search by text content if selector starts with "text:"
      if (!el && selector.startsWith("text:")) {
        const text = selector.slice(5);
        document.querySelectorAll("button, [role='button']").forEach((btn) => {
          if (!el && btn.textContent?.includes(text)) {
            el = btn as HTMLElement;
          }
        });
      }

      if (el) {
        if (type === "click") {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          setTimeout(() => el!.click(), 300);
        } else if (type === "fill" && value) {
          const input = el as HTMLInputElement;
          const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, "value"
          )?.set;
          if (nativeSetter) {
            nativeSetter.call(input, value);
            input.dispatchEvent(new Event("input", { bubbles: true }));
          }
        }
      }
    }

    if (currentStep < steps.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      onComplete();
    }
  }, [currentStep, steps, onComplete]);

  // Auto-advance timer
  useEffect(() => {
    const step = steps[currentStep];
    if (!step?.autoAdvanceMs || !isActive) return;
    const timer = setTimeout(() => {
      handleNext();
    }, step.autoAdvanceMs);
    return () => clearTimeout(timer);
  }, [currentStep, steps, isActive, handleNext]);

  const handleSkip = () => {
    setIsVisible(false);
    onSkip();
  };

  if (!isActive || !step) return null;

  const placement = step.placement || "bottom";
  const tooltipHeight = 220; // approximate
  const tooltipPos = targetRect
    ? getTooltipPosition(targetRect, placement, tooltipHeight)
    : { top: window.innerHeight / 2 - 110, left: window.innerWidth / 2 - TOOLTIP_WIDTH / 2 };

  const spotlightX = targetRect ? targetRect.left - PADDING : 0;
  const spotlightY = targetRect ? targetRect.top - PADDING : 0;
  const spotlightW = targetRect ? targetRect.width + PADDING * 2 : 0;
  const spotlightH = targetRect ? targetRect.height + PADDING * 2 : 0;

  const isLastStep = currentStep === steps.length - 1;

  return (
    <AnimatePresence>
      {isVisible && (
        <div className="fixed inset-0 z-[9999]" style={{ pointerEvents: "none" }}>
          {/* SVG overlay with spotlight cutout */}
          <motion.svg
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 h-full w-full"
            style={{ pointerEvents: "auto" }}
            onClick={handleSkip}
          >
            <defs>
              <mask id="tour-spotlight-mask">
                <rect x="0" y="0" width="100%" height="100%" fill="white" />
                {targetRect && (
                  <rect
                    x={spotlightX}
                    y={spotlightY}
                    width={spotlightW}
                    height={spotlightH}
                    rx="8"
                    ry="8"
                    fill="black"
                  />
                )}
              </mask>
            </defs>
            <rect
              x="0"
              y="0"
              width="100%"
              height="100%"
              fill="rgba(0,0,0,0.5)"
              mask="url(#tour-spotlight-mask)"
            />
          </motion.svg>

          {/* Spotlight border glow */}
          {targetRect && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed rounded-lg border-2 border-[#635BFF]/60"
              style={{
                top: spotlightY,
                left: spotlightX,
                width: spotlightW,
                height: spotlightH,
                boxShadow: "0 0 0 4px rgba(99,91,255,0.15)",
                pointerEvents: "none",
              }}
            />
          )}

          {/* Tooltip */}
          <motion.div
            ref={tooltipRef}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className={cn(
              "fixed rounded-xl border border-gray-200 bg-white p-5 shadow-2xl",
              "text-gray-900"
            )}
            style={{
              top: tooltipPos.top,
              left: tooltipPos.left,
              width: TOOLTIP_WIDTH,
              pointerEvents: "auto",
              zIndex: 10000,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Step counter */}
            <p className="mb-1 text-xs font-medium text-[#635BFF]">
              Step {currentStep + 1} of {steps.length}
            </p>

            {/* Title */}
            <h3 className="mb-2 text-base font-bold text-gray-900">
              {step.title}
            </h3>

            {/* Description */}
            <p className="mb-4 text-sm leading-relaxed text-gray-600">
              {step.description}
            </p>

            {/* Actions */}
            <div className="flex items-center justify-between">
              <button
                onClick={handleSkip}
                className="text-xs font-medium text-gray-400 transition-colors hover:text-gray-600"
              >
                Skip Tour
              </button>
              <button
                onClick={handleNext}
                className={cn(
                  "rounded-lg px-4 py-2 text-sm font-semibold text-white transition-all",
                  "bg-[#635BFF] hover:bg-[#5349e0] active:scale-95"
                )}
              >
                {isLastStep ? "Get Started \u2192" : "Next \u2192"}
              </button>
            </div>

            {/* Progress dots */}
            <div className="mt-3 flex items-center justify-center gap-1.5">
              {steps.map((_, i) => (
                <div
                  key={i}
                  className={cn(
                    "h-1.5 rounded-full transition-all",
                    i === currentStep
                      ? "w-4 bg-[#635BFF]"
                      : i < currentStep
                        ? "w-1.5 bg-[#635BFF]/40"
                        : "w-1.5 bg-gray-300"
                  )}
                />
              ))}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
