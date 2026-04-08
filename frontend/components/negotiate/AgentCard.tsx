"use client";

import React from "react";
import { cn } from "@/lib/utils";
import type { AgentInfo } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { MovingBorder } from "@/components/ui/aceternity/moving-border";
import {
  Users,
  BarChart3,
  ShieldAlert,
  Lightbulb,
  CheckCircle2,
  Check,
  AlertCircle,
  Loader2,
  Clock,
} from "lucide-react";

const AGENT_ICONS: Record<string, React.ReactNode> = {
  comparables: <Users className="h-5 w-5" />,
  offer_analysis: <BarChart3 className="h-5 w-5" />,
  clause_risk: <ShieldAlert className="h-5 w-5" />,
  strategy: <Lightbulb className="h-5 w-5" />,
  fact_check: <CheckCircle2 className="h-5 w-5" />,
};

const STATUS_CONFIG = {
  idle: {
    badge: "secondary" as const,
    label: "Waiting",
    icon: <Clock className="h-3 w-3" />,
  },
  active: {
    badge: "default" as const,
    label: "Active",
    icon: <Loader2 className="h-3 w-3 animate-spin" />,
  },
  complete: {
    badge: "success" as const,
    label: "Done",
    icon: <Check className="h-3 w-3" />,
  },
  error: {
    badge: "destructive" as const,
    label: "Error",
    icon: <AlertCircle className="h-3 w-3" />,
  },
};

interface AgentCardProps {
  agent: AgentInfo;
}

export default function AgentCard({ agent }: AgentCardProps) {
  const config = STATUS_CONFIG[agent.status];
  const icon = AGENT_ICONS[agent.id] ?? <Lightbulb className="h-5 w-5" />;

  const cardContent = (
    <div
      className={cn(
        "relative flex min-w-[140px] flex-col items-center gap-2 rounded-lg border bg-card p-4 transition-all",
        agent.status === "active" && "border-primary pulse-glow animate-glow-breathe agent-active-border",
        agent.status === "complete" && "border-negotiate-success/50",
        agent.status === "error" && "border-negotiate-danger/50",
        agent.status === "idle" && "border-border opacity-60"
      )}
    >
      <div
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-full",
          agent.status === "active" && "bg-primary/20 text-primary",
          agent.status === "complete" &&
            "bg-negotiate-success/20 text-negotiate-success",
          agent.status === "error" &&
            "bg-negotiate-danger/20 text-negotiate-danger",
          agent.status === "idle" && "bg-muted text-muted-foreground"
        )}
      >
        {icon}
      </div>

      <span className="text-center text-xs font-medium">{agent.name}</span>

      <Badge variant={config.badge} className="gap-1 text-[10px]">
        {config.icon}
        {config.label}
      </Badge>

      <p className="text-center text-[10px] leading-tight text-muted-foreground">
        {agent.description}
      </p>
    </div>
  );

  if (agent.status === "active") {
    return (
      <MovingBorder
        duration={3000}
        containerClassName="rounded-lg"
        borderClassName="bg-[radial-gradient(rgba(99,91,255,0.8)_40%,rgba(0,212,255,0.6)_60%,transparent_80%)]"
      >
        {cardContent}
      </MovingBorder>
    );
  }

  return cardContent;
}
