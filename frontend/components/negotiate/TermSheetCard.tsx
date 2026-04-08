"use client";

import React from "react";
import { cn, formatEUR } from "@/lib/utils";
import type { NegotiationRound, TermSheet } from "@/lib/types";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DollarSign,
  Calendar,
  Shield,
  Image,
  FileCheck,
  ArrowUpDown,
} from "lucide-react";

interface TermSheetCardProps {
  round: NegotiationRound;
  previousRound?: NegotiationRound | null;
}

function hasChanged(
  field: keyof TermSheet,
  current: NegotiationRound,
  previous?: NegotiationRound | null
): boolean {
  if (!previous || !current.term_sheet || !previous.term_sheet) return false;
  return current.term_sheet[field] !== previous.term_sheet[field];
}

function TermRow({
  label,
  value,
  changed,
  icon,
}: {
  label: string;
  value: string | React.ReactNode;
  changed?: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between rounded px-3 py-2 text-sm",
        changed && "bg-negotiate-warning/10"
      )}
    >
      <span className="flex items-center gap-2 text-muted-foreground">
        {icon}
        {label}
      </span>
      <span
        className={cn("font-medium", changed && "text-negotiate-warning")}
      >
        {value}
      </span>
    </div>
  );
}

export default function TermSheetCard({
  round,
  previousRound,
}: TermSheetCardProps) {
  const ts = round.term_sheet;
  if (!ts) return null;

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">{ts.player_name}</CardTitle>
            <CardDescription>{ts.position}</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              variant={round.side === "club" ? "default" : "success"}
              className={cn(
                round.side === "club"
                  ? "bg-negotiate-club/20 text-negotiate-club"
                  : "bg-negotiate-player/20 text-negotiate-player"
              )}
            >
              {round.side === "club" ? "Club Offer" : "Player Counter"}
            </Badge>
            <Badge
              variant={
                round.action === "ACCEPT"
                  ? "success"
                  : round.action === "WALK_AWAY"
                    ? "destructive"
                    : "outline"
              }
            >
              {round.action}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-1">
        <div className="mb-3 rounded-lg bg-primary/10 p-3 text-center">
          <p className="text-xs text-muted-foreground">Total Value</p>
          <p className="text-2xl font-bold text-primary">
            {formatEUR(ts.total_value_eur)}
          </p>
        </div>

        <div className="space-y-0.5">
          <TermRow
            label="Base Salary"
            value={formatEUR(ts.base_salary_eur)}
            changed={hasChanged("base_salary_eur", round, previousRound)}
            icon={<DollarSign className="h-3.5 w-3.5" />}
          />
          <TermRow
            label="Signing Bonus"
            value={formatEUR(ts.signing_bonus_eur)}
            changed={hasChanged("signing_bonus_eur", round, previousRound)}
            icon={<DollarSign className="h-3.5 w-3.5" />}
          />
          <TermRow
            label="Performance Bonus"
            value={formatEUR(ts.performance_bonus_eur)}
            changed={hasChanged("performance_bonus_eur", round, previousRound)}
            icon={<DollarSign className="h-3.5 w-3.5" />}
          />
          <TermRow
            label="Contract Years"
            value={`${ts.contract_years} yr${ts.contract_years !== 1 ? "s" : ""}`}
            changed={hasChanged("contract_years", round, previousRound)}
            icon={<Calendar className="h-3.5 w-3.5" />}
          />
          <TermRow
            label="Option Year"
            value={ts.option_year ? "Yes" : "No"}
            changed={hasChanged("option_year", round, previousRound)}
            icon={<Calendar className="h-3.5 w-3.5" />}
          />
          <TermRow
            label="Release Clause"
            value={formatEUR(ts.release_clause_eur)}
            changed={hasChanged("release_clause_eur", round, previousRound)}
            icon={<Shield className="h-3.5 w-3.5" />}
          />
          <TermRow
            label="Image Rights"
            value={`${ts.image_rights_pct}%`}
            changed={hasChanged("image_rights_pct", round, previousRound)}
            icon={<Image className="h-3.5 w-3.5" />}
          />
          <TermRow
            label="No-Trade Clause"
            value={ts.no_trade_clause ? "Yes" : "No"}
            changed={hasChanged("no_trade_clause", round, previousRound)}
            icon={<FileCheck className="h-3.5 w-3.5" />}
          />
        </div>

        {round.constraint_violations.length > 0 && (
          <div className="mt-3 rounded-lg border border-negotiate-danger/30 bg-negotiate-danger/10 p-3">
            <p className="mb-1 text-xs font-medium text-negotiate-danger">
              Constraint Violations
            </p>
            <ul className="space-y-0.5 text-xs text-negotiate-danger/80">
              {round.constraint_violations.map((v, i) => (
                <li key={i} className="flex items-start gap-1">
                  <ArrowUpDown className="mt-0.5 h-3 w-3 shrink-0" />
                  {v}
                </li>
              ))}
            </ul>
          </div>
        )}

        {round.reasoning && (
          <div className="mt-3 rounded-lg bg-muted p-3">
            <p className="text-xs text-muted-foreground">{round.reasoning}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
