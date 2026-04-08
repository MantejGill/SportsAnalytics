"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { UserSide } from "@/lib/types";
import { Building2, User, Handshake, ArrowRight } from "lucide-react";
import { SparklesText } from "@/components/ui/aceternity/sparkles-text";
import { BackgroundBeamsWithCollision } from "@/components/ui/aceternity/background-beams-with-collision";

interface SideSelectorProps {
  onStart: (params: {
    side: UserSide;
    playerName: string;
    clubName: string;
    budgetEur: number;
    priorities: string[];
    walkAwayThreshold: number;
  }) => void;
}

export default function SideSelector({ onStart }: SideSelectorProps) {
  const [selectedSide, setSelectedSide] = useState<UserSide | null>(null);
  const [playerName, setPlayerName] = useState("Bukayo Saka");
  const [clubName, setClubName] = useState("Arsenal");
  const [budgetEur, setBudgetEur] = useState(25_000_000);
  const [priorities, setPriorities] = useState(
    "low base salary, performance incentives, release clause"
  );
  const [walkAwayThreshold, setWalkAwayThreshold] = useState(30_000_000);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSide) return;
    onStart({
      side: selectedSide,
      playerName,
      clubName,
      budgetEur,
      priorities: priorities.split(",").map((p) => p.trim()),
      walkAwayThreshold,
    });
  };

  return (
    <div className="relative flex flex-1 flex-col items-center justify-center gap-8 p-8">
      {/* Animated background beams */}
      <BackgroundBeamsWithCollision className="z-0" />

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 text-center"
      >
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
          <Handshake className="h-8 w-8 text-primary" />
        </div>
        <h1 className="mb-2 text-3xl font-bold tracking-tight">
          <SparklesText colors={["#635BFF", "#00D4FF", "#6E7BFF"]}>
            Choose Your Side
          </SparklesText>
        </h1>
        <p className="max-w-md text-muted-foreground">
          Pick a side, then negotiate against the AI. Your War Room advisors
          will analyze every offer before you decide.
        </p>
      </motion.div>

      {/* Side cards */}
      <div className="relative z-10 flex flex-col gap-4 sm:flex-row">
        <motion.button
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          type="button"
          onClick={() => setSelectedSide("club")}
          className={cn(
            "group flex w-64 flex-col items-center gap-3 rounded-xl border-2 bg-card p-6 text-center transition-all hover:border-negotiate-club/60 hover:bg-negotiate-club/5",
            selectedSide === "club"
              ? "border-negotiate-club bg-negotiate-club/10 shadow-lg shadow-negotiate-club/10"
              : "border-border"
          )}
        >
          <div
            className={cn(
              "flex h-14 w-14 items-center justify-center rounded-full transition-colors",
              selectedSide === "club"
                ? "bg-negotiate-club/20 text-negotiate-club"
                : "bg-muted text-muted-foreground group-hover:bg-negotiate-club/10 group-hover:text-negotiate-club"
            )}
          >
            <Building2 className="h-7 w-7" />
          </div>
          <h3 className="text-lg font-semibold">Club / General Manager</h3>
          <p className="text-sm text-muted-foreground">
            Negotiate to sign a player within your budget
          </p>
        </motion.button>

        <motion.button
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
          type="button"
          onClick={() => setSelectedSide("player")}
          className={cn(
            "group flex w-64 flex-col items-center gap-3 rounded-xl border-2 bg-card p-6 text-center transition-all hover:border-negotiate-player/60 hover:bg-negotiate-player/5",
            selectedSide === "player"
              ? "border-negotiate-player bg-negotiate-player/10 shadow-lg shadow-negotiate-player/10"
              : "border-border"
          )}
        >
          <div
            className={cn(
              "flex h-14 w-14 items-center justify-center rounded-full transition-colors",
              selectedSide === "player"
                ? "bg-negotiate-player/20 text-negotiate-player"
                : "bg-muted text-muted-foreground group-hover:bg-negotiate-player/10 group-hover:text-negotiate-player"
            )}
          >
            <User className="h-7 w-7" />
          </div>
          <h3 className="text-lg font-semibold">Player Agent</h3>
          <p className="text-sm text-muted-foreground">
            Maximize your client's contract value
          </p>
        </motion.button>
      </div>

      {/* Setup form */}
      {selectedSide && (
        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          onSubmit={handleSubmit}
          data-tour="setup-form"
          className="relative z-10 w-full max-w-lg space-y-4 rounded-xl border border-border bg-card p-6"
        >
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Negotiation Setup
          </h3>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Player Name
              </label>
              <input
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Club Name
              </label>
              <input
                type="text"
                value={clubName}
                onChange={(e) => setClubName(e.target.value)}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Budget (EUR)
              </label>
              <input
                type="number"
                value={budgetEur}
                onChange={(e) => setBudgetEur(Number(e.target.value))}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                min={0}
                step={1_000_000}
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Walk-Away Threshold (EUR)
              </label>
              <input
                type="number"
                value={walkAwayThreshold}
                onChange={(e) => setWalkAwayThreshold(Number(e.target.value))}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                min={0}
                step={1_000_000}
                required
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Priorities (comma-separated)
            </label>
            <input
              type="text"
              value={priorities}
              onChange={(e) => setPriorities(e.target.value)}
              placeholder="low base salary, performance incentives"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              required
            />
          </div>

          <button
            type="submit"
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Start Negotiation
            <ArrowRight className="h-4 w-4" />
          </button>
        </motion.form>
      )}
    </div>
  );
}
