"use client";

import React from "react";
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import { useNegotiationEvents } from "@/hooks/useNegotiationEvents";
import { useChatLoading } from "@/contexts/ChatLoadingContext";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import SideSelector from "@/components/negotiate/SideSelector";
import IncomingOfferCard from "@/components/negotiate/IncomingOfferCard";
import WarRoomPanel from "@/components/negotiate/WarRoomPanel";
import DecisionPanel from "@/components/negotiate/DecisionPanel";
import AgentPipeline from "@/components/negotiate/AgentPipeline";
import OfferTimeline from "@/components/negotiate/OfferTimeline";
import TermSheetCard from "@/components/negotiate/TermSheetCard";
import NegotiationMetrics from "@/components/negotiate/NegotiationMetrics";
import ExportButton from "@/components/negotiate/ExportButton";
import GuidedTour from "@/components/demo/GuidedTour";
import DemoButton from "@/components/demo/DemoButton";
import { DEMO_TOUR_STEPS } from "@/components/demo/demoTourSteps";
import type { UserSide } from "@/lib/types";
import { cn, formatEUR } from "@/lib/utils";
import {
  Handshake,
  Clock,
  FileText,
  BarChart3,
  Building2,
  User,
  Trophy,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { TextGenerateEffect } from "@/components/ui/aceternity/text-generate-effect";
import { SparklesText } from "@/components/ui/aceternity/sparkles-text";

// ---------------------------------------------------------------------------
// COMPLETE screen: shown when negotiation is done
// ---------------------------------------------------------------------------
function CompleteScreen() {
  const status = useNegotiationStore((s) => s.status);
  const rounds = useNegotiationStore((s) => s.rounds);
  const playerName = useNegotiationStore((s) => s.playerName);
  const clubName = useNegotiationStore((s) => s.clubName);
  const clearAll = useNegotiationStore((s) => s.clearAll);

  const latestRound = rounds.length > 0 ? rounds[rounds.length - 1] : null;
  const finalSheet = latestRound?.term_sheet;

  const isAccepted = status === "accepted";
  const isWalkedAway = status === "walked_away";

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="text-center"
      >
        <div
          className={`mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full ${
            isAccepted
              ? "bg-negotiate-success/20"
              : "bg-negotiate-danger/20"
          }`}
        >
          {isAccepted ? (
            <Trophy className="h-10 w-10 text-negotiate-success" />
          ) : isWalkedAway ? (
            <XCircle className="h-10 w-10 text-negotiate-danger" />
          ) : (
            <AlertTriangle className="h-10 w-10 text-negotiate-warning" />
          )}
        </div>

        <h1 className="mb-2 text-2xl font-bold">
          {isAccepted
            ? <SparklesText colors={["#635BFF", "#00D4FF", "#6E7BFF"]}>Deal Accepted!</SparklesText>
            : isWalkedAway
              ? "Negotiation Ended"
              : "Max Rounds Reached"}
        </h1>
        <p className="text-muted-foreground">
          {isAccepted
            ? `${playerName} and ${clubName} reached an agreement.`
            : isWalkedAway
              ? "One side walked away from the table."
              : "The maximum number of negotiation rounds was reached without agreement."}
        </p>
      </motion.div>

      {/* Final term sheet summary */}
      {finalSheet && (
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="w-full max-w-md rounded-xl border border-border bg-card p-6"
        >
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Final Terms
          </h3>
          <div className="mb-4 rounded-lg bg-primary/10 p-3 text-center">
            <p className="text-xs text-muted-foreground">Total Value</p>
            <p className="text-2xl font-bold text-primary">
              {formatEUR(finalSheet.total_value_eur)}
            </p>
          </div>
          <div className="space-y-1.5 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Base Salary</span>
              <span className="font-medium">
                {formatEUR(finalSheet.base_salary_eur)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Signing Bonus</span>
              <span className="font-medium">
                {formatEUR(finalSheet.signing_bonus_eur)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Contract</span>
              <span className="font-medium">
                {finalSheet.contract_years} years
                {finalSheet.option_year ? " + option" : ""}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Release Clause</span>
              <span className="font-medium">
                {formatEUR(finalSheet.release_clause_eur)}
              </span>
            </div>
          </div>
        </motion.div>
      )}

      <div className="flex items-center gap-3">
        <ExportButton />
        <button
          onClick={clearAll}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
        >
          New Negotiation
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function HomePage() {
  const [isTourActive, setIsTourActive] = React.useState(false);
  const [tourWasInterrupted, setTourWasInterrupted] = React.useState(false);
  const status = useNegotiationStore((s) => s.status);
  const rounds = useNegotiationStore((s) => s.rounds);
  const userSide = useNegotiationStore((s) => s.userSide);
  const playerName = useNegotiationStore((s) => s.playerName);
  const clubName = useNegotiationStore((s) => s.clubName);
  const marketContext = useNegotiationStore((s) => s.marketContext);
  const awaitingDecision = useNegotiationStore((s) => s.awaitingDecision);
  const startNeg = useNegotiationStore((s) => s.startNegotiation);
  const setUserSide = useNegotiationStore((s) => s.setUserSide);
  const setSetupParams = useNegotiationStore((s) => s.setSetupParams);
  const setStatus = useNegotiationStore((s) => s.setStatus);
  const { connect } = useNegotiationEvents();
  const { setIsLoading } = useChatLoading();

  const latestRound = rounds.length > 0 ? rounds[rounds.length - 1] : null;
  const previousRound = rounds.length > 1 ? rounds[rounds.length - 2] : null;

  // The opponent name and label for display
  const opponentName =
    userSide === "club" ? playerName : clubName;
  const opponentLabel =
    userSide === "club" ? "Player" : "Club";

  const submitDecision = useNegotiationStore((s) => s.submitDecision);
  const warRoomResults = useNegotiationStore((s) => s.warRoomResults);

  // Keep CopilotKit aware of live negotiation state so it can proactively advise
  useCopilotReadable({
    description: "Current negotiation state — updated in real time as offers arrive and war room analyzes",
    value: {
      status,
      awaitingDecision,
      currentRound: rounds.length,
      playerName,
      clubName,
      userSide,
      latestOffer: latestRound?.term_sheet
        ? {
            side: latestRound.side,
            round: latestRound.round_number,
            baseSalaryEur: latestRound.term_sheet.base_salary_eur,
            totalValueEur: latestRound.term_sheet.total_value_eur,
            contractYears: latestRound.term_sheet.contract_years,
            noTradeClause: latestRound.term_sheet.no_trade_clause,
            releaseClauseEur: latestRound.term_sheet.release_clause_eur,
          }
        : null,
      warRoomRecommendation: awaitingDecision && warRoomResults
        ? {
            action: warRoomResults.recommended_action,
            counterSalaryEur: warRoomResults.recommended_counter?.base_salary_eur ?? null,
            reasoning: warRoomResults.reasoning,
            medianComparableSalaryEur: (warRoomResults.comparables as any)?.median_comparable_salary_eur ?? null,
            salaryRange: (marketContext as any)?.salary_range ?? null,
          }
        : null,
    },
  });

  // CopilotKit action: START a negotiation from chat
  useCopilotAction({
    name: "startNegotiation",
    description:
      "Start a new contract negotiation. The user tells you the player, club, budget, side, and priorities.",
    parameters: [
      { name: "player_name", type: "string", description: "Player name", required: true },
      { name: "club_name", type: "string", description: "Club name", required: true },
      { name: "budget_eur", type: "number", description: "Annual budget in EUR", required: true },
      { name: "user_side", type: "string", description: "'club' or 'player'", required: true },
      { name: "priorities", type: "string", description: "Comma-separated priorities", required: true },
      { name: "walk_away_threshold_eur", type: "number", description: "Walk-away salary EUR", required: false },
    ],
    handler: async ({ player_name, club_name, budget_eur, user_side, priorities, walk_away_threshold_eur }) => {
      const side = (user_side === "club" ? "club" : "player") as UserSide;
      const prioList = priorities.split(",").map((p: string) => p.trim());
      const walkAway = walk_away_threshold_eur || Math.round(budget_eur * 0.7);

      await handleStart({
        side,
        playerName: player_name,
        clubName: club_name,
        budgetEur: budget_eur,
        priorities: prioList,
        walkAwayThreshold: walkAway,
      });

      return `Negotiation started for ${player_name} with ${club_name}. You're playing as the ${side === "player" ? "Player Agent" : "Club GM"}. The AI opponent is making their opening offer. Watch the dashboard for the War Room analysis, then tell me your decision: accept, counter (with a number), or walk away.`;
    },
  });

  // CopilotKit action: SUBMIT a decision (accept/counter/walk away) from chat
  useCopilotAction({
    name: "submitDecision",
    description:
      "Submit the user's negotiation decision: ACCEPT the current offer, COUNTER with a new offer, or WALK_AWAY. Only call this when the system is awaiting a user decision (war room analysis is complete).",
    parameters: [
      { name: "action", type: "string", description: "ACCEPT, COUNTER, or WALK_AWAY", required: true },
      { name: "base_salary_eur", type: "number", description: "Base salary for counter-offer", required: false },
      { name: "signing_bonus_eur", type: "number", description: "Signing bonus", required: false },
      { name: "performance_bonus_eur", type: "number", description: "Performance bonus", required: false },
      { name: "contract_years", type: "number", description: "Contract years", required: false },
      { name: "release_clause_eur", type: "number", description: "Release clause EUR", required: false },
    ],
    handler: async ({ action, base_salary_eur, signing_bonus_eur, performance_bonus_eur, contract_years, release_clause_eur }) => {
      const store = useNegotiationStore.getState();
      if (!store.awaitingDecision) {
        return "Not ready for a decision yet — waiting for the AI opponent's offer and War Room analysis to complete. Please wait a moment.";
      }

      const actionUpper = action.toUpperCase();
      if (!["ACCEPT", "COUNTER", "WALK_AWAY"].includes(actionUpper)) {
        return "Invalid action. Please say 'accept', 'counter at [amount]', or 'walk away'.";
      }

      let termSheet = undefined;
      if (actionUpper === "COUNTER") {
        const recommended = store.warRoomResults?.recommended_counter;
        const baseSal = base_salary_eur || recommended?.base_salary_eur || 10000000;
        const signBonus = signing_bonus_eur || recommended?.signing_bonus_eur || 0;
        const perfBonus = performance_bonus_eur || recommended?.performance_bonus_eur || 0;
        const years = contract_years || recommended?.contract_years || 4;
        termSheet = {
          player_name: store.playerName || "Player",
          position: recommended?.position || "CM",
          base_salary_eur: baseSal,
          signing_bonus_eur: signBonus,
          performance_bonus_eur: perfBonus,
          contract_years: years,
          option_year: false,
          release_clause_eur: release_clause_eur || recommended?.release_clause_eur || 0,
          total_value_eur: baseSal * years + signBonus + perfBonus * years,
          image_rights_pct: recommended?.image_rights_pct || 20,
          no_trade_clause: true,
        };
      }

      try {
        await submitDecision(actionUpper as any, termSheet);

        if (actionUpper === "ACCEPT") {
          return "You accepted the deal! The negotiation is complete.";
        } else if (actionUpper === "WALK_AWAY") {
          return "You walked away from the negotiation. No deal was reached.";
        } else {
          const salaryStr = termSheet ? `€${(termSheet.base_salary_eur / 1000000).toFixed(1)}M` : "";
          return `Counter-offer submitted at ${salaryStr} base salary. Waiting for the opponent's response and new War Room analysis...`;
        }
      } catch (err: any) {
        return `Decision failed: ${err.message}. Please try again.`;
      }
    },
  });

  // CopilotKit action: get current context for advisory questions
  useCopilotAction({
    name: "getNegotiationContext",
    description:
      "Get the current negotiation state including rounds, market data, and war room analysis. Use this to answer user questions about the negotiation.",
    parameters: [],
    handler: async () => {
      const store = useNegotiationStore.getState();
      return JSON.stringify({
        status: store.status,
        currentRound: store.currentRound,
        userSide: store.userSide,
        playerName: store.playerName,
        clubName: store.clubName,
        rounds: store.rounds,
        marketContext: store.marketContext,
        warRoomResults: store.warRoomResults,
        awaitingDecision: store.awaitingDecision,
      });
    },
  });

  // Handle side selection and negotiation start
  const handleStart = async (params: {
    side: UserSide;
    playerName: string;
    clubName: string;
    budgetEur: number;
    priorities: string[];
    walkAwayThreshold: number;
  }) => {
    setIsLoading(true);
    toast.info(
      `Starting negotiation as ${params.side === "club" ? "Club GM" : "Player Agent"}...`
    );

    try {
      setUserSide(params.side);
      setSetupParams({
        playerName: params.playerName,
        clubName: params.clubName,
        budgetEur: params.budgetEur,
        priorities: params.priorities,
        walkAwayThreshold: params.walkAwayThreshold,
      });

      const response = await fetch("/api/backend/negotiate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_name: params.playerName,
          club_name: params.clubName,
          budget_eur: params.budgetEur,
          max_years: 5,
          priorities: params.priorities,
          user_side: params.side,
          walk_away_threshold_eur: params.walkAwayThreshold,
        }),
      });

      if (!response.ok) {
        const err = await response.text();
        throw new Error(`Backend error: ${err}`);
      }

      const data = await response.json();
      const requestId = data.request_id;
      console.log("[handleStart] backend returned request_id:", requestId);

      startNeg(requestId);
      connect(requestId);
      console.log("[handleStart] startNeg + connect called for:", requestId);

      toast.success(
        "Negotiation started! The AI opponent will make the first move."
      );
    } catch (error: any) {
      setStatus("idle");
      toast.error(`Failed to start negotiation: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Determine current phase
  const isSetup = status === "idle";
  const isComplete =
    status === "accepted" || status === "walked_away" || status === "max_rounds";
  const isNegotiating = status === "negotiating";

  return (
    <main className={cn("flex h-screen flex-col bg-background", isSetup ? "overflow-y-auto" : "overflow-hidden", isNegotiating && "dashboard-ambient dot-grid")}>
      {/* Guided Tour */}
      <GuidedTour
        steps={DEMO_TOUR_STEPS}
        isActive={isTourActive}
        onComplete={() => { setIsTourActive(false); setTourWasInterrupted(false); }}
        onSkip={() => { setIsTourActive(false); setTourWasInterrupted(true); }}
      />

      {/* Demo Button */}
      {(isSetup || tourWasInterrupted) && !isTourActive && (
        <DemoButton
          onStart={() => setIsTourActive(true)}
          tourWasInterrupted={tourWasInterrupted}
        />
      )}

      {/* Header */}
      <header data-tour="app-header" className="flex shrink-0 items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <Handshake className="h-6 w-6 text-primary" />
          <h1 className="text-lg font-semibold tracking-tight gradient-text">
            Auto-Negotiate
          </h1>
          {userSide && (isNegotiating || isComplete) && (
            <Badge
              variant={userSide === "club" ? "default" : "success"}
              className={cn(
                "ml-2 gap-1 text-[10px]",
                userSide === "club"
                  ? "bg-blue-500/15 text-blue-700 border-blue-500/30 dark:text-blue-400"
                  : "bg-green-500/15 text-green-700 border-green-500/30 dark:text-green-400"
              )}
            >
              {userSide === "club" ? (
                <Building2 className="h-3 w-3" />
              ) : (
                <User className="h-3 w-3" />
              )}
              Playing as {userSide === "club" ? "Club GM" : "Player Agent"}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-3">
          {isNegotiating && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-negotiate-success" />
              Live
            </div>
          )}
          {isNegotiating && awaitingDecision && (
            <Badge variant="warning" className="animate-pulse text-[10px] bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-500/20 dark:text-amber-400 dark:border-amber-500/30">
              Your Turn
            </Badge>
          )}
          {isComplete && <ExportButton />}
        </div>
      </header>

      {/* --- SETUP --- */}
      {isSetup && (
        <div data-tour="side-selector">
          <SideSelector onStart={handleStart} />
        </div>
      )}

      {/* --- COMPLETE --- */}
      {isComplete && <CompleteScreen />}

      {/* --- NEGOTIATING --- */}
      {isNegotiating && (
        <div className="flex flex-1 overflow-hidden">
          {/* Left panel: War Room + Decision (70%) */}
          <div className="flex w-[70%] flex-col overflow-y-auto border-r border-border p-3 space-y-3">
            {/* Agent pipeline strip */}
            <AgentPipeline />

            {/* Incoming offer */}
            {latestRound && latestRound.term_sheet && (
              <div data-tour="offer-card">
                <IncomingOfferCard
                  round={latestRound}
                  previousRound={previousRound}
                  marketContext={marketContext}
                  opponentName={opponentName}
                  walkAwayThreshold={useNegotiationStore.getState().walkAwayThreshold}
                />
              </div>
            )}

            {!latestRound && (
              <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border p-10 text-center">
                <Clock className="h-8 w-8 text-muted-foreground/40" />
                <TextGenerateEffect
                  words="Waiting for the AI opponent's opening offer..."
                  className="text-sm"
                  textClassName="text-muted-foreground"
                  duration={0.4}
                />
              </div>
            )}

            {/* War Room */}
            <WarRoomPanel />

            {/* Decision Panel */}
            <div data-tour="decision-panel">
              <DecisionPanel />
            </div>
          </div>

          {/* Right panel: Timeline + Metrics (30%) */}
          <div className="flex w-[30%] flex-col overflow-hidden">
            <Tabs
              defaultValue="metrics"
              className="flex flex-1 flex-col overflow-hidden"
            >
              <div className="shrink-0 border-b border-border px-3">
                <TabsList className="h-9">
                  <TabsTrigger value="metrics" className="gap-1.5 text-xs">
                    <BarChart3 className="h-3.5 w-3.5" />
                    Metrics
                  </TabsTrigger>
                  <TabsTrigger value="timeline" className="gap-1.5 text-xs" data-tour="timeline-tab">
                    <Clock className="h-3.5 w-3.5" />
                    Timeline
                  </TabsTrigger>
                  <TabsTrigger value="termsheet" className="gap-1.5 text-xs">
                    <FileText className="h-3.5 w-3.5" />
                    Sheet
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent
                value="metrics"
                className="flex-1 overflow-y-auto data-[state=inactive]:hidden"
              >
                <NegotiationMetrics />
              </TabsContent>

              <TabsContent
                value="timeline"
                className="flex flex-1 flex-col overflow-hidden data-[state=inactive]:hidden"
              >
                <OfferTimeline />
              </TabsContent>

              <TabsContent
                value="termsheet"
                className="flex-1 overflow-y-auto p-4 data-[state=inactive]:hidden"
              >
                {latestRound ? (
                  <TermSheetCard
                    round={latestRound}
                    previousRound={previousRound}
                  />
                ) : (
                  <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted-foreground">
                    Waiting for the first offer...
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </div>
        </div>
      )}
    </main>
  );
}
