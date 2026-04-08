"use client";

import React from "react";
import { cn, formatEUR } from "@/lib/utils";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  BarChart3,
  Target,
  ShieldCheck,
  Activity,
  Gauge,
  Users,
  Zap,
} from "lucide-react";

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "accepted"
      ? "success"
      : status === "walked_away" || status === "max_rounds"
        ? "destructive"
        : status === "negotiating"
          ? "default"
          : "secondary";

  return (
    <Badge variant={variant as any} className="text-xs">
      {status === "idle"
        ? "Ready"
        : status === "negotiating"
          ? "Negotiating"
          : status === "accepted"
            ? "Deal Accepted"
            : status === "walked_away"
              ? "Walked Away"
              : "Max Rounds Reached"}
    </Badge>
  );
}

function ScoreCard({
  label,
  score,
  description,
  icon: Icon,
}: {
  label: string;
  score: number;
  description: string;
  icon: React.ElementType;
}) {
  const color =
    score > 70
      ? "text-negotiate-success"
      : score >= 40
        ? "text-negotiate-warning"
        : "text-negotiate-danger";
  const bgColor =
    score > 70
      ? "bg-negotiate-success"
      : score >= 40
        ? "bg-negotiate-warning"
        : "bg-negotiate-danger";

  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={cn("h-4 w-4", color)} />
            <span className="text-xs font-semibold">{label}</span>
          </div>
          <span className={cn("text-lg font-bold", color)}>{score}</span>
        </div>
        <Progress
          value={score}
          className="h-1.5"
          /* The indicator color is set via the progress component styles */
        />
        <p className="mt-1.5 text-[10px] text-muted-foreground">
          {description}
        </p>
      </CardContent>
    </Card>
  );
}

function DualBarCard({
  label,
  clubScore,
  playerScore,
  icon: Icon,
}: {
  label: string;
  clubScore: number;
  playerScore: number;
  icon: React.ElementType;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-3 flex items-center gap-2">
          <Icon className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold">{label}</span>
        </div>
        <div className="space-y-2">
          <div>
            <div className="mb-0.5 flex items-center justify-between text-[10px]">
              <span className="text-muted-foreground">Club Satisfaction</span>
              <span className="font-medium">{clubScore}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-blue-500 transition-all"
                style={{ width: `${clubScore}%` }}
              />
            </div>
          </div>
          <div>
            <div className="mb-0.5 flex items-center justify-between text-[10px]">
              <span className="text-muted-foreground">Player Satisfaction</span>
              <span className="font-medium">{playerScore}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-green-500 transition-all"
                style={{ width: `${playerScore}%` }}
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function NegotiationMetrics() {
  const rounds = useNegotiationStore((s) => s.rounds);
  const currentRound = useNegotiationStore((s) => s.currentRound);
  const maxRounds = useNegotiationStore((s) => s.maxRounds);
  const status = useNegotiationStore((s) => s.status);
  const salaryGap = useNegotiationStore((s) => s.getSalaryGap());
  const marketContext = useNegotiationStore((s) => s.marketContext);

  // Compliance rate: rounds without constraint violations / total rounds
  const compliantRounds = rounds.filter(
    (r) => r.constraint_violations.length === 0
  ).length;
  const complianceRate =
    rounds.length > 0 ? Math.round((compliantRounds / rounds.length) * 100) : 100;

  // Chart data: salary offers over rounds
  const chartData = React.useMemo(() => {
    const grouped: Record<
      number,
      { round: number; club?: number; player?: number }
    > = {};

    for (const r of rounds) {
      if (!r.term_sheet) continue;
      if (!grouped[r.round_number]) {
        grouped[r.round_number] = { round: r.round_number };
      }
      if (r.side === "club") {
        grouped[r.round_number].club = r.term_sheet.total_value_eur;
      } else {
        grouped[r.round_number].player = r.term_sheet.total_value_eur;
      }
    }

    return Object.values(grouped).sort((a, b) => a.round - b.round);
  }, [rounds]);

  const gapPercent = Math.round(salaryGap * 100);
  // Only show convergence when both sides have made offers
  const clubOffers = rounds.filter((r) => r.side === "club" && r.term_sheet);
  const playerOffers = rounds.filter((r) => r.side === "player" && r.term_sheet);
  const hasBothSides = clubOffers.length > 0 && playerOffers.length > 0;
  const convergencePercent = hasBothSides ? Math.max(0, 100 - gapPercent) : 0;

  // --- Validation Metrics ---
  // Market Realism: is latest offer base_salary within the SALARY range (not transfer value range)?
  const latestRound = rounds.length > 0 ? rounds[rounds.length - 1] : null;
  const marketRealism = React.useMemo(() => {
    if (!latestRound?.term_sheet || !marketContext) return 50;
    const baseSalary = latestRound.term_sheet.base_salary_eur;
    // Use salary_range (low/mid/high) NOT transfer value (p25/median/p75)
    const salaryRange = marketContext.salary_range;
    const low = salaryRange?.low_eur || marketContext.p25_eur * 0.08;
    const mid = salaryRange?.mid_eur || marketContext.median_eur * 0.1;
    const high = salaryRange?.high_eur || marketContext.p75_eur * 0.12;

    if (baseSalary >= low && baseSalary <= high) {
      // Within range: score 60-100 based on distance from mid
      const distFromMid = Math.abs(baseSalary - mid);
      const rangeHalf = (high - low) / 2;
      return Math.max(60, Math.min(100, Math.round(100 - (distFromMid / rangeHalf) * 40)));
    } else if (baseSalary < low) {
      // Below range: 0-59 proportional to how far below
      const deviation = (low - baseSalary) / low;
      return Math.max(0, Math.round(50 - deviation * 100));
    } else {
      // Above range: 0-59
      const deviation = (baseSalary - high) / high;
      return Math.max(0, Math.round(50 - deviation * 100));
    }
  }, [latestRound, marketContext]);

  // Outcome Quality: compare offer salary to salary_range midpoint, not ML transfer value
  const { clubSatisfaction, playerSatisfaction } = React.useMemo(() => {
    if (!latestRound?.term_sheet || !marketContext) {
      return { clubSatisfaction: 50, playerSatisfaction: 50 };
    }
    const baseSalary = latestRound.term_sheet.base_salary_eur;
    // Use salary mid (annual salary benchmark), NOT median_eur (which is transfer value)
    const salaryMid = (marketContext as any).salary_range?.mid_eur || 0;
    const salaryHigh = (marketContext as any).salary_range?.high_eur || salaryMid * 1.5;
    const salaryLow = (marketContext as any).salary_range?.low_eur || salaryMid * 0.6;
    const salarySpan = salaryHigh - salaryLow || salaryMid;

    if (!salaryMid) return { clubSatisfaction: 50, playerSatisfaction: 50 };

    // Club happy when salary is low (near/below low end); player happy when near/above high end
    let club = Math.round(
      Math.max(0, Math.min(100, 100 - ((baseSalary - salaryLow) / salarySpan) * 100))
    );
    let player = Math.round(
      Math.max(0, Math.min(100, ((baseSalary - salaryLow) / salarySpan) * 100))
    );
    if (status === "accepted") {
      club = Math.min(100, club + 5);
      player = Math.min(100, player + 5);
    }
    return { clubSatisfaction: club, playerSatisfaction: player };
  }, [latestRound, marketContext, status]);

  // Efficiency: rounds used so far (only meaningful once negotiation starts)
  // Show as rounds remaining to make it actionable, not a misleading % at round 1
  const roundsUsed = currentRound;
  const roundsLeft = Math.max(0, maxRounds - currentRound);
  // Efficiency score = how early a deal was made relative to max rounds (only at end)
  const efficiency = status === "accepted" || status === "walked_away" || status === "max_rounds"
    ? Math.round((roundsLeft / maxRounds) * 100)
    : null;

  return (
    <div className="space-y-4 p-4" data-tour="metrics-panel">
      {/* Top stats row */}
      <div className="grid grid-cols-2 gap-2">
        <Card>
          <CardContent className="flex flex-col items-center justify-center p-2">
            <BarChart3 className="mb-0.5 h-4 w-4 text-primary" />
            <p className="text-lg font-bold">
              {currentRound}/{maxRounds}
            </p>
            <p className="text-[10px] text-muted-foreground">Round</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex flex-col items-center justify-center p-2">
            <Target className="mb-0.5 h-4 w-4 text-negotiate-warning" />
            <p className="text-lg font-bold">{convergencePercent}%</p>
            <p className="text-[10px] text-muted-foreground">Convergence</p>
          </CardContent>
        </Card>

        <Card data-tour="constraint-checker">
          <CardContent className="flex flex-col items-center justify-center p-2">
            <ShieldCheck className="mb-0.5 h-4 w-4 text-negotiate-success" />
            <p className="text-lg font-bold">{complianceRate}%</p>
            <p className="text-[10px] text-muted-foreground">Compliance</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex flex-col items-center justify-center p-2">
            <Activity className="mb-0.5 h-4 w-4 text-primary" />
            <StatusBadge status={status} />
            <p className="mt-1 text-xs text-muted-foreground">Status</p>
          </CardContent>
        </Card>
      </div>

      {/* Salary gap progress */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Salary Gap Convergence</CardTitle>
        </CardHeader>
        <CardContent>
          <Progress value={convergencePercent} className="h-2" />
          <div className="mt-1 flex justify-between text-xs text-muted-foreground">
            <span>Far apart</span>
            <span>{convergencePercent}%</span>
            <span>Agreement</span>
          </div>
        </CardContent>
      </Card>

      {/* Validation Metrics */}
      {rounds.length > 0 && (
        <>
          <div className="flex items-center gap-2 pt-2">
            <Gauge className="h-4 w-4 text-primary" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Validation Metrics
            </h3>
          </div>

          <ScoreCard
            label="Market Realism"
            score={marketRealism}
            description="How close the deal is to market comparables"
            icon={Gauge}
          />

          <DualBarCard
            label="Outcome Quality"
            clubScore={clubSatisfaction}
            playerScore={playerSatisfaction}
            icon={Users}
          />

          <Card>
            <CardContent className="p-4">
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-primary" />
                  <span className="text-xs font-semibold">
                    {efficiency !== null ? "Efficiency" : "Rounds Left"}
                  </span>
                </div>
                <span className="text-lg font-bold text-primary">
                  {efficiency !== null ? `${efficiency}%` : `${roundsLeft}/${maxRounds}`}
                </span>
              </div>
              <Progress
                value={efficiency !== null ? efficiency : (roundsLeft / maxRounds) * 100}
                className="h-1.5"
              />
              <p className="mt-1.5 text-[10px] text-muted-foreground">
                {efficiency !== null
                  ? "Deal reached early — fewer rounds is better"
                  : `${roundsUsed} round${roundsUsed !== 1 ? "s" : ""} used · ${roundsLeft} remaining`}
              </p>
            </CardContent>
          </Card>
        </>
      )}

      {/* Chart */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">
              Offer Values Over Rounds
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <XAxis
                    dataKey="round"
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: number) =>
                      `${(v / 1_000_000).toFixed(1)}M`
                    }
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(222 47% 8%)",
                      border: "1px solid hsl(217 33% 17%)",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(value: number) => formatEUR(value)}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: "12px" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="club"
                    name="Club"
                    stroke="hsl(217 91% 60%)"
                    strokeWidth={2}
                    dot={{ fill: "hsl(217 91% 60%)", r: 4 }}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="player"
                    name="Player"
                    stroke="hsl(142 71% 45%)"
                    strokeWidth={2}
                    dot={{ fill: "hsl(142 71% 45%)", r: 4 }}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
