"use client";

import React from "react";
import { motion } from "framer-motion";
import { cn, formatEUR } from "@/lib/utils";
import type { NegotiationRound, MarketContext } from "@/lib/types";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import { Badge } from "@/components/ui/badge";
import {
  Building2,
  UserRound,
  BrainCircuit,
  ArrowUp,
  ArrowDown,
  Minus,
  TrendingUp,
} from "lucide-react";

interface IncomingOfferCardProps {
  round: NegotiationRound;
  previousRound?: NegotiationRound | null;
  marketContext?: MarketContext | null;
  opponentName: string;
  walkAwayThreshold?: number;
}

function ChangeIndicator({
  current,
  previous,
}: {
  current: number;
  previous?: number;
}) {
  if (previous === undefined || previous === current) return null;
  const isUp = current > previous;
  return (
    <span
      className={cn(
        "ml-1 inline-flex items-center text-[10px]",
        isUp ? "text-negotiate-success" : "text-negotiate-danger"
      )}
    >
      {isUp ? (
        <ArrowUp className="h-3 w-3" />
      ) : (
        <ArrowDown className="h-3 w-3" />
      )}
    </span>
  );
}

function MarketBand({
  value,
  p25,
  median,
  p75,
}: {
  value: number;
  p25: number;
  median: number;
  p75: number;
}) {
  let color = "text-negotiate-warning";
  let label = "Mid-Market";
  if (value >= p75) {
    color = "text-negotiate-success";
    label = "Above P75";
  } else if (value >= median) {
    color = "text-negotiate-success";
    label = "Above Median";
  } else if (value < p25) {
    color = "text-negotiate-danger";
    label = "Below P25";
  }

  return (
    <span className={cn("flex items-center gap-1 text-[10px] font-medium", color)}>
      <TrendingUp className="h-3 w-3" />
      {label}
    </span>
  );
}

export default function IncomingOfferCard({
  round,
  previousRound,
  marketContext,
  opponentName,
  walkAwayThreshold,
}: IncomingOfferCardProps) {
  const ts = round.term_sheet;
  if (!ts) return null;

  const prevTs = previousRound?.term_sheet;
  const isClub = round.side === "club";
  const salaryRange = (marketContext as any)?.salary_range;
  const belowWalkAway = walkAwayThreshold && ts.base_salary_eur < walkAwayThreshold;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="rounded-xl border-2 border-primary/30 bg-card p-4 glass-card text-foreground"
    >
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isClub ? (
            <Building2 className="h-5 w-5 text-negotiate-club" />
          ) : (
            <UserRound className="h-5 w-5 text-negotiate-player" />
          )}
          <h3 className="text-base font-semibold text-foreground">
            {opponentName}&apos;s {round.action === "PROPOSE" ? "Offer" : "Counter"} &mdash; Round{" "}
            {round.round_number}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant={isClub ? "default" : "success"}
            className={cn(
              isClub
                ? "bg-blue-100 text-blue-700 border-blue-200 dark:bg-negotiate-club/20 dark:text-negotiate-club dark:border-negotiate-club/30"
                : "bg-green-100 text-green-700 border-green-200 dark:bg-negotiate-player/20 dark:text-negotiate-player dark:border-negotiate-player/30"
            )}
          >
            {isClub ? "Club" : "Player"}
          </Badge>
          {marketContext && (
            <MarketBand
              value={ts.total_value_eur}
              p25={marketContext.p25_eur}
              median={marketContext.median_eur}
              p75={marketContext.p75_eur}
            />
          )}
        </div>
      </div>

      {/* Total value highlight */}
      <div className="mb-4 rounded-lg bg-primary/10 p-3 text-center">
        <p className="text-xs font-medium text-foreground/60">Total Contract Value</p>
        <p className="text-2xl font-bold text-primary">
          {formatEUR(ts.total_value_eur)}
          <ChangeIndicator
            current={ts.total_value_eur}
            previous={prevTs?.total_value_eur}
          />
        </p>
      </div>

      {/* Quick verdict badges */}
      <div className="mb-3 flex flex-wrap gap-2">
        {salaryRange && (
          <span className={cn(
            "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-medium",
            ts.base_salary_eur >= salaryRange.mid_eur
              ? "bg-green-100 text-green-800 dark:bg-green-500/20 dark:text-green-400"
              : ts.base_salary_eur >= salaryRange.low_eur
                ? "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-400"
                : "bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-400"
          )}>
            {ts.base_salary_eur >= salaryRange.mid_eur ? "At/Above Market"
              : ts.base_salary_eur >= salaryRange.low_eur ? "Below Median"
              : "Below Market Range"}
          </span>
        )}
        {belowWalkAway && (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-400 px-2.5 py-0.5 text-[10px] font-medium">
            Below Your Walk-Away ({formatEUR(walkAwayThreshold!)})
          </span>
        )}
      </div>

      {/* Term details grid */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
        <TermRow
          label="Base Salary"
          value={formatEUR(ts.base_salary_eur)}
          previous={prevTs?.base_salary_eur}
          current={ts.base_salary_eur}
        />
        <TermRow
          label="Signing Bonus"
          value={formatEUR(ts.signing_bonus_eur)}
          previous={prevTs?.signing_bonus_eur}
          current={ts.signing_bonus_eur}
        />
        <TermRow
          label="Performance Bonus"
          value={formatEUR(ts.performance_bonus_eur)}
          previous={prevTs?.performance_bonus_eur}
          current={ts.performance_bonus_eur}
        />
        <TermRow
          label="Contract Years"
          value={`${ts.contract_years} yr${ts.contract_years !== 1 ? "s" : ""}`}
          previous={prevTs?.contract_years}
          current={ts.contract_years}
        />
        <TermRow
          label="Release Clause"
          value={formatEUR(ts.release_clause_eur)}
          previous={prevTs?.release_clause_eur}
          current={ts.release_clause_eur}
        />
        <TermRow
          label="Image Rights"
          value={`${ts.image_rights_pct}%`}
          previous={prevTs?.image_rights_pct}
          current={ts.image_rights_pct}
        />
        <TermRow
          label="Option Year"
          value={ts.option_year ? "Yes" : "No"}
        />
        <TermRow
          label="No-Trade Clause"
          value={ts.no_trade_clause ? "Yes" : "No"}
        />
      </div>

      {/* Opponent Reasoning - collapsible */}
      {round.reasoning && (
        <details className="mt-3">
          <summary className="cursor-pointer text-[11px] font-medium text-muted-foreground hover:text-foreground">
            Opponent&apos;s reasoning...
          </summary>
          <div className="mt-1 rounded-lg bg-muted/50 p-2">
            <p className="text-[11px] leading-relaxed text-muted-foreground">{round.reasoning}</p>
          </div>
        </details>
      )}

    </motion.div>
  );
}

function WarRoomReasoning() {
  const warRoomResults = useNegotiationStore((s) => s.warRoomResults);
  if (!warRoomResults?.reasoning) return null;

  return (
    <details className="mt-2" open>
      <summary className="cursor-pointer text-[11px] font-semibold text-primary hover:text-primary/80 flex items-center gap-1">
        <BrainCircuit className="h-3.5 w-3.5" />
        War Room Advisory (Decision Aggregator)
      </summary>
      <div className="mt-1.5 rounded-lg border border-primary/20 bg-primary/5 p-3">
        <p className="text-[11px] leading-relaxed text-foreground/80">
          {warRoomResults.reasoning}
        </p>
      </div>
    </details>
  );
}

function TermRow({
  label,
  value,
  previous,
  current,
}: {
  label: string;
  value: string;
  previous?: number;
  current?: number;
}) {
  const changed = previous !== undefined && current !== undefined && previous !== current;
  return (
    <div
      className={cn(
        "flex items-center justify-between rounded px-2 py-1.5 text-sm",
        changed && "bg-negotiate-warning/10"
      )}
    >
      <span className="text-foreground/70">{label}</span>
      <span className={cn("font-medium", changed && "text-negotiate-warning")}>
        {value}
        {current !== undefined && previous !== undefined && (
          <ChangeIndicator current={current} previous={previous} />
        )}
      </span>
    </div>
  );
}
