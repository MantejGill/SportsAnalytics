"use client";

import React from "react";
import { motion } from "framer-motion";
import { cn, formatEUR } from "@/lib/utils";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import type { WarRoomResults } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import {
  Users,
  BarChart3,
  ShieldAlert,
  Lightbulb,
  CheckCircle2,
  Loader2,
  AlertTriangle,
  TrendingUp,
  XCircle,
  ExternalLink,
} from "lucide-react";
import { MovingBorder } from "@/components/ui/aceternity/moving-border";

const WAR_ROOM_AGENTS = [
  {
    id: "comparables",
    title: "Comparables",
    icon: Users,
    color: "text-blue-400",
    bgColor: "bg-blue-400/10",
    borderColor: "border-blue-400/30",
  },
  {
    id: "offer_analysis",
    title: "Offer Analyzer",
    icon: BarChart3,
    color: "text-amber-400",
    bgColor: "bg-amber-400/10",
    borderColor: "border-amber-400/30",
  },
  {
    id: "clause_risk",
    title: "Clause & Risk",
    icon: ShieldAlert,
    color: "text-red-400",
    bgColor: "bg-red-400/10",
    borderColor: "border-red-400/30",
  },
  {
    id: "strategy",
    title: "Strategy",
    icon: Lightbulb,
    color: "text-green-400",
    bgColor: "bg-green-400/10",
    borderColor: "border-green-400/30",
  },
  {
    id: "fact_check",
    title: "Fact-Check",
    icon: CheckCircle2,
    color: "text-purple-400",
    bgColor: "bg-purple-400/10",
    borderColor: "border-purple-400/30",
  },
];

function ComparablesList({
  warRoomResults,
}: {
  warRoomResults: WarRoomResults;
}) {
  const comparables = warRoomResults.comparables;
  const playerList = (comparables as any)?.similar_players || (comparables as any)?.comparables || [];
  if (!playerList || playerList.length === 0)
    return null;

  return (
    <div className="mt-2 space-y-1.5">
      {playerList.map((p: any, i: number) => {
        const salaryStr =
          p.salary != null
            ? formatEUR(p.salary)
            : p.salary_eur != null
              ? formatEUR(p.salary_eur)
              : "";
        const citation = p.citation || "";
        const sourceUrl = p.source_url || "";
        const sourceName = p.source || "";

        const age = p.age_at_signing || p.age || "?";
        const year = p.year || "?";
        const fee = p.transfer_fee_eur;
        const playerPosition = (comparables as any)?.player_position || "?";
        const playerAge = (comparables as any)?.player_age || "?";

        return (
          <div key={i} className="group relative rounded bg-muted/30 px-2 py-1.5 cursor-pointer hover:bg-muted/50 transition-colors">
            <div className="text-[11px] font-medium text-foreground">
              {p.name} — {salaryStr ? `${salaryStr}/yr` : "?"}{" "}
              <span className="text-muted-foreground">at {p.club || "?"} ({year})</span>
            </div>
            {(sourceName || sourceUrl) && (
              <div className="mt-0.5 flex items-center gap-1">
                {sourceUrl ? (
                  <a
                    href={sourceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-0.5 text-[10px] text-primary hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Source: {sourceName || "Link"}
                    <ExternalLink className="h-2.5 w-2.5" />
                  </a>
                ) : (
                  <span className="text-[10px] text-muted-foreground">
                    Source: {sourceName}
                  </span>
                )}
              </div>
            )}
            {/* Hover tooltip: why comparable */}
            <div className="invisible group-hover:visible absolute left-0 top-full z-50 mt-1 w-64 rounded-lg border border-border bg-card p-2.5 shadow-lg">
              <p className="text-[10px] font-semibold text-primary mb-1">Why comparable?</p>
              <ul className="text-[10px] text-foreground/80 space-y-0.5">
                <li>• Similar position to {playerPosition}</li>
                <li>• Signed at age {age} (player is {playerAge})</li>
                {fee ? <li>• Transfer fee: {formatEUR(fee)}</li> : null}
                <li>• Deal signed in {year}{p.club ? ` with ${p.club}` : ""}</li>
                <li>• Salary {salaryStr}/yr — {
                  p.salary_eur > (comparables as any)?.average_comparable_salary_eur
                    ? "above" : "below"
                } avg comparable ({formatEUR((comparables as any)?.average_comparable_salary_eur || 0)})</li>
              </ul>
            </div>
          </div>
        );
      })}

      {/* Transfer value citation and range methodology */}
      {(comparables as any).transfer_value_citation && (
        <div className="mt-1 text-[10px] text-muted-foreground italic">
          {(comparables as any).transfer_value_citation}
        </div>
      )}
      {(comparables as any).range_methodology && (
        <div className="mt-0.5 text-[10px] text-muted-foreground italic">
          {(comparables as any).range_methodology}
        </div>
      )}
    </div>
  );
}

function AgentAnalysisCard({
  agentConfig,
  status,
  content,
  warnings,
  warRoomResults,
}: {
  agentConfig: (typeof WAR_ROOM_AGENTS)[number];
  status: "idle" | "active" | "complete" | "error";
  content?: string;
  warnings?: string[];
  warRoomResults?: WarRoomResults | null;
}) {
  const Icon = agentConfig.icon;
  const isComparables = agentConfig.id === "comparables";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-lg border bg-card p-4 transition-all card-hover-lift",
        status === "active" && "border-primary pulse-glow",
        status === "complete" && agentConfig.borderColor,
        status === "error" && "border-negotiate-danger/50",
        status === "idle" && "border-border opacity-50"
      )}
    >
      {/* Header */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "flex h-7 w-7 items-center justify-center rounded-full",
              status === "complete" ? agentConfig.bgColor : "bg-muted"
            )}
          >
            <Icon
              className={cn(
                "h-4 w-4",
                status === "complete"
                  ? agentConfig.color
                  : "text-muted-foreground"
              )}
            />
          </div>
          <span className="text-xs font-semibold">{agentConfig.title}</span>
        </div>

        {status === "active" && (
          <Badge variant="default" className="gap-1 text-[10px]">
            <Loader2 className="h-3 w-3 animate-spin" />
            Analyzing
          </Badge>
        )}
        {status === "complete" && (
          <Badge variant="success" className="gap-1 text-[10px]">
            <CheckCircle2 className="h-3 w-3" />
            Done
          </Badge>
        )}
        {status === "idle" && (
          <Badge variant="secondary" className="text-[10px]">
            Waiting
          </Badge>
        )}
      </div>

      {/* Content */}
      {content && (
        <AnalysisText text={content} />
      )}

      {/* Comparables detail list with citations */}
      {isComparables && status === "complete" && warRoomResults && (
        <ComparablesList warRoomResults={warRoomResults} />
      )}

      {/* Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="mt-2 space-y-1">
          {warnings.map((w, i) => (
            <div
              key={i}
              className="flex items-start gap-1.5 rounded bg-amber-50 dark:bg-negotiate-warning/10 px-2 py-1 border border-amber-200 dark:border-negotiate-warning/20"
            >
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-600 dark:text-negotiate-warning" />
              <span className="text-[10px] text-amber-800 dark:text-negotiate-warning">{w}</span>
            </div>
          ))}
        </div>
      )}

      {status === "idle" && !content && (
        <p className="text-[10px] italic text-muted-foreground/50">
          Waiting for offer...
        </p>
      )}
    </motion.div>
  );
}

/**
 * Renders analysis text, detecting and styling [Data: ...] attribution blocks.
 */
function AnalysisText({ text }: { text: string }) {
  // Split into lines first, then handle [Data:] attribution patterns
  const lines = text.split("\n");

  return (
    <div className="text-xs leading-relaxed text-foreground/70 space-y-0.5">
      {lines.map((line, li) => {
        const parts = line.split(/(\[Data:[^\]]+\])/g);
        const isBullet = line.trimStart().startsWith("•");

        return (
          <div key={li} className={isBullet ? "pl-1" : ""}>
            {parts.map((part, pi) => {
              if (part.startsWith("[Data:")) {
                return (
                  <span
                    key={pi}
                    className="mt-0.5 inline-block rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary"
                  >
                    {part}
                  </span>
                );
              }
              return <React.Fragment key={pi}>{part}</React.Fragment>;
            })}
          </div>
        );
      })}
    </div>
  );
}

export default function WarRoomPanel() {
  const agents = useNegotiationStore((s) => s.agents);
  const warRoomResults = useNegotiationStore((s) => s.warRoomResults);

  const getAgentStatus = (id: string) => {
    const agent = agents.find((a) => a.id === id);
    return agent?.status || "idle";
  };

  const getContent = (id: string): string | undefined => {
    if (!warRoomResults) return undefined;
    const key = id as keyof WarRoomResults;
    const section = warRoomResults[key];
    if (section && typeof section === "object") {
      // Try "analysis" first, then "summary" (backend uses summary)
      const s = section as any;
      return s.analysis || s.summary || undefined;
    }
    return undefined;
  };

  const getWarnings = (id: string): string[] | undefined => {
    if (!warRoomResults) return undefined;
    if (id === "clause_risk") {
      const risks = (warRoomResults.clause_risk?.risks || []).map((r: any) =>
        typeof r === "string" ? r : `${r.clause || r.risk_level || ""}: ${r.explanation || r.recommendation || JSON.stringify(r)}`
      );
      const missing = (warRoomResults.clause_risk?.missing_protections || []).map((m: any) =>
        typeof m === "string" ? m : JSON.stringify(m)
      );
      return [...risks, ...missing];
    }
    if (id === "fact_check" && warRoomResults.fact_check?.issues?.length > 0) {
      return warRoomResults.fact_check.issues;
    }
    return undefined;
  };

  return (
    <div className="space-y-4" data-tour="war-room">
      {/* War Room header */}
      <div className="flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10">
          <TrendingUp className="h-3.5 w-3.5 text-primary" />
        </div>
        <h2 className="text-sm font-semibold">War Room</h2>
        {warRoomResults && (
          <Badge variant="success" className="text-[10px]">
            Analysis Complete
          </Badge>
        )}
      </div>

      {/* Agent grid: 3 + 2 layout */}
      <div className="grid grid-cols-3 gap-3">
        {WAR_ROOM_AGENTS.slice(0, 3).map((agent) => (
          <AgentAnalysisCard
            key={agent.id}
            agentConfig={agent}
            status={getAgentStatus(agent.id)}
            content={getContent(agent.id)}
            warnings={getWarnings(agent.id)}
            warRoomResults={warRoomResults}
          />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3">
        {WAR_ROOM_AGENTS.slice(3).map((agent) => (
          <AgentAnalysisCard
            key={agent.id}
            agentConfig={agent}
            status={getAgentStatus(agent.id)}
            content={getContent(agent.id)}
            warnings={getWarnings(agent.id)}
            warRoomResults={warRoomResults}
          />
        ))}
      </div>

      {/* Decision Aggregator — synthesized reasoning from all 5 agents */}
      {warRoomResults?.reasoning && (
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
          <div className="mb-1.5 flex items-center gap-1.5">
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/20">
              <TrendingUp className="h-3 w-3 text-primary" />
            </div>
            <h3 className="text-xs font-semibold text-primary">Decision Aggregator</h3>
            <span className="text-[9px] text-muted-foreground">(synthesized from 5 agents)</span>
          </div>
          <p className="text-xs leading-relaxed text-foreground/80">
            {warRoomResults.reasoning}
          </p>
        </div>
      )}

      {/* Aggregated recommendation banner */}
      {warRoomResults && (
        <div data-tour="recommendation">
        <MovingBorder
          duration={3000}
          containerClassName="rounded-lg"
          borderClassName={cn(
            warRoomResults.recommended_action === "ACCEPT"
              ? "bg-[radial-gradient(rgba(16,185,129,0.8)_40%,transparent_60%)]"
              : warRoomResults.recommended_action === "COUNTER"
                ? "bg-[radial-gradient(rgba(99,91,255,0.8)_40%,rgba(0,212,255,0.6)_60%,transparent_80%)]"
                : "bg-[radial-gradient(rgba(239,68,68,0.8)_40%,transparent_60%)]"
          )}
        >
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "rounded-lg border-2 p-4",
              warRoomResults.recommended_action === "ACCEPT"
                ? "border-green-500 bg-green-50 dark:bg-green-500/15"
                : warRoomResults.recommended_action === "COUNTER"
                  ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-500/15"
                  : "border-red-500 bg-red-50 dark:bg-red-500/15"
            )}
          >
            <div className="flex items-center gap-3">
              {warRoomResults.recommended_action === "ACCEPT" ? (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-500">
                  <CheckCircle2 className="h-5 w-5 text-white" />
                </div>
              ) : warRoomResults.recommended_action === "COUNTER" ? (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-500">
                  <TrendingUp className="h-5 w-5 text-white" />
                </div>
              ) : (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-500">
                  <XCircle className="h-5 w-5 text-white" />
                </div>
              )}
              <div>
                <span className="text-sm font-bold text-foreground">
                  Recommended:{" "}
                  <span
                    className={cn(
                      warRoomResults.recommended_action === "ACCEPT"
                        ? "text-green-700 dark:text-green-400"
                        : warRoomResults.recommended_action === "COUNTER"
                          ? "text-indigo-700 dark:text-indigo-400"
                          : "text-red-700 dark:text-red-400"
                    )}
                  >
                    {warRoomResults.recommended_action}
                  </span>
                </span>
                {warRoomResults.recommended_counter && (
                  <span className="ml-2 text-sm font-semibold text-foreground">
                    at{" "}
                    {formatEUR(
                      warRoomResults.recommended_counter.base_salary_eur
                    )}
                    /yr base
                  </span>
                )}
              </div>
            </div>
          </motion.div>
        </MovingBorder>
        </div>
      )}
    </div>
  );
}
