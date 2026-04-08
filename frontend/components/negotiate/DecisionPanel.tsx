"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import type { DecisionAction, TermSheet } from "@/lib/types";
import CounterOfferForm from "./CounterOfferForm";
import { CheckCircle2, ArrowLeftRight, XCircle, Gavel } from "lucide-react";
import { toast } from "sonner";

export default function DecisionPanel() {
  const [showCounter, setShowCounter] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const awaitingDecision = useNegotiationStore((s) => s.awaitingDecision);
  const currentRound = useNegotiationStore((s) => s.currentRound);
  const warRoomResults = useNegotiationStore((s) => s.warRoomResults);
  const playerName = useNegotiationStore((s) => s.playerName);
  const submitDecision = useNegotiationStore((s) => s.submitDecision);
  const getLatestOffer = useNegotiationStore((s) => s.getLatestOffer);

  if (!awaitingDecision) return null;

  const latestOffer = getLatestOffer();

  const handleDecision = async (action: DecisionAction, termSheet?: TermSheet) => {
    setSubmitting(true);
    try {
      await submitDecision(action, termSheet);
      setShowCounter(false);
      if (action === "ACCEPT") {
        toast.success("Deal accepted! Finalizing contract...");
      } else if (action === "WALK_AWAY") {
        toast.info("You walked away from the negotiation.");
      } else {
        toast.info("Counter-offer submitted. Waiting for opponent...");
      }
    } catch (error: any) {
      toast.error(`Failed to submit decision: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Your Move banner */}
      <div className="flex items-center justify-between rounded-xl border-2 border-negotiate-warning/50 bg-negotiate-warning/10 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-negotiate-warning/20">
            <Gavel className="h-5 w-5 text-negotiate-warning" />
          </div>
          <div>
            <h2 className="text-base font-bold text-negotiate-warning">
              Your Move
            </h2>
            <p className="text-xs text-muted-foreground">
              Round {currentRound} &mdash; Review the war room analysis and
              decide
            </p>
          </div>
        </div>
      </div>

      {/* Decision buttons */}
      <AnimatePresence mode="wait">
        {!showCounter ? (
          <motion.div
            key="buttons"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="grid grid-cols-3 gap-3"
          >
            <button
              disabled={submitting}
              onClick={() => handleDecision("ACCEPT")}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border-2 border-negotiate-success/30 bg-negotiate-success/5 p-4 transition-all hover:border-negotiate-success/60 hover:bg-negotiate-success/10",
                submitting && "pointer-events-none opacity-50"
              )}
            >
              <CheckCircle2 className="h-6 w-6 text-negotiate-success" />
              <span className="text-sm font-semibold text-negotiate-success">
                ACCEPT
              </span>
              <span className="text-[10px] text-muted-foreground">
                Sign the deal
              </span>
            </button>

            <button
              disabled={submitting}
              onClick={() => setShowCounter(true)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border-2 border-primary/30 bg-primary/5 p-4 transition-all hover:border-primary/60 hover:bg-primary/10",
                submitting && "pointer-events-none opacity-50"
              )}
            >
              <ArrowLeftRight className="h-6 w-6 text-primary" />
              <span className="text-sm font-semibold text-primary">
                COUNTER
              </span>
              <span className="text-[10px] text-muted-foreground">
                Edit & send counter
              </span>
            </button>

            <button
              disabled={submitting}
              onClick={() => handleDecision("WALK_AWAY")}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border-2 border-negotiate-danger/30 bg-negotiate-danger/5 p-4 transition-all hover:border-negotiate-danger/60 hover:bg-negotiate-danger/10",
                submitting && "pointer-events-none opacity-50"
              )}
            >
              <XCircle className="h-6 w-6 text-negotiate-danger" />
              <span className="text-sm font-semibold text-negotiate-danger">
                WALK AWAY
              </span>
              <span className="text-[10px] text-muted-foreground">
                End negotiation
              </span>
            </button>
          </motion.div>
        ) : (
          <motion.div
            key="counter-form"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <CounterOfferForm
              recommended={warRoomResults?.recommended_counter || null}
              latestOffer={latestOffer?.term_sheet || null}
              playerName={playerName}
              onSubmit={(ts) => handleDecision("COUNTER", ts)}
              onCancel={() => setShowCounter(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
