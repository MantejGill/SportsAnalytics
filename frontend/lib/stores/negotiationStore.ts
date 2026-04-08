import { create } from "zustand";
import type {
  AgentInfo,
  AgentStatus,
  DecisionAction,
  MarketContext,
  NegotiationRound,
  NegotiationStatus,
  TermSheet,
  UserSide,
  WarRoomResults,
} from "@/lib/types";

const DEFAULT_AGENTS: AgentInfo[] = [
  {
    id: "comparables",
    name: "Comparables",
    status: "idle",
    description: "Finds similar players and their deals",
  },
  {
    id: "offer_analysis",
    name: "Offer Analyzer",
    status: "idle",
    description: "Breaks down the offer vs. market",
  },
  {
    id: "clause_risk",
    name: "Clause & Risk",
    status: "idle",
    description: "Flags risky or missing clauses",
  },
  {
    id: "strategy",
    name: "Strategy",
    status: "idle",
    description: "BATNA/ZOPA context and recommendations",
  },
  {
    id: "fact_check",
    name: "Fact-Check",
    status: "idle",
    description: "Verifies numbers add up correctly",
  },
];

interface NegotiationStore {
  // State
  rounds: NegotiationRound[];
  agents: AgentInfo[];
  status: NegotiationStatus;
  activeAgent: string | null;
  currentRound: number;
  maxRounds: number;
  marketContext: MarketContext | null;
  isConnected: boolean;
  requestId: string | null;
  logs: string[];

  // War Room / HITL state
  userSide: UserSide | null;
  warRoomResults: WarRoomResults | null;
  awaitingDecision: boolean;
  walkAwayThreshold: number;
  playerName: string;
  clubName: string;
  budgetEur: number;
  priorities: string[];

  // Actions
  addRound: (round: NegotiationRound) => void;
  updateAgent: (agentId: string, status: AgentStatus) => void;
  setStatus: (status: NegotiationStatus) => void;
  setActiveAgent: (agentId: string | null) => void;
  setMarketContext: (ctx: MarketContext) => void;
  setConnected: (connected: boolean) => void;
  setRequestId: (id: string | null) => void;
  setMaxRounds: (max: number) => void;
  addLog: (msg: string) => void;
  startNegotiation: (requestId: string) => void;
  clearAll: () => void;

  // War Room actions
  setUserSide: (side: UserSide) => void;
  setWarRoomResults: (results: WarRoomResults) => void;
  setAwaitingDecision: (awaiting: boolean) => void;
  setWalkAwayThreshold: (threshold: number) => void;
  setSetupParams: (params: {
    playerName: string;
    clubName: string;
    budgetEur: number;
    priorities: string[];
    walkAwayThreshold: number;
  }) => void;
  submitDecision: (
    action: DecisionAction,
    termSheet?: TermSheet
  ) => Promise<void>;

  // Computed helpers
  getActiveAgents: () => AgentInfo[];
  getCompletedAgents: () => AgentInfo[];
  getLatestOffer: () => NegotiationRound | null;
  getSalaryGap: () => number;
  getOpponentSide: () => "club" | "player";
}

export const useNegotiationStore = create<NegotiationStore>((set, get) => ({
  rounds: [],
  agents: DEFAULT_AGENTS.map((a) => ({ ...a })),
  status: "idle",
  activeAgent: null,
  currentRound: 0,
  maxRounds: 10,
  marketContext: null,
  isConnected: false,
  requestId: null,
  logs: [],

  // War Room state
  userSide: null,
  warRoomResults: null,
  awaitingDecision: false,
  walkAwayThreshold: 0,
  playerName: "",
  clubName: "",
  budgetEur: 0,
  priorities: [],

  addRound: (round) =>
    set((state) => ({
      rounds: [...state.rounds, round],
      currentRound: round.round_number,
    })),

  updateAgent: (agentId, status) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.id === agentId ? { ...a, status } : a
      ),
    })),

  setStatus: (status) => set({ status }),

  setActiveAgent: (agentId) => set({ activeAgent: agentId }),

  setMarketContext: (ctx) => set({ marketContext: ctx }),

  setConnected: (connected) => set({ isConnected: connected }),

  setRequestId: (id) => set({ requestId: id }),

  setMaxRounds: (max) => set({ maxRounds: max }),

  addLog: (msg) =>
    set((state) => ({
      logs: [...state.logs, `[${new Date().toISOString()}] ${msg}`],
    })),

  startNegotiation: (requestId) =>
    set({
      requestId,
      status: "negotiating",
      rounds: [],
      currentRound: 0,
      activeAgent: null,
      logs: [],
      agents: DEFAULT_AGENTS.map((a) => ({ ...a })),
      marketContext: null,
      warRoomResults: null,
      awaitingDecision: false,
    }),

  clearAll: () =>
    set({
      rounds: [],
      agents: DEFAULT_AGENTS.map((a) => ({ ...a })),
      status: "idle",
      activeAgent: null,
      currentRound: 0,
      marketContext: null,
      isConnected: false,
      requestId: null,
      logs: [],
      userSide: null,
      warRoomResults: null,
      awaitingDecision: false,
      walkAwayThreshold: 0,
      playerName: "",
      clubName: "",
      budgetEur: 0,
      priorities: [],
    }),

  // War Room actions
  setUserSide: (side) => set({ userSide: side }),

  setWarRoomResults: (results) =>
    set({
      warRoomResults: results,
      awaitingDecision: true,
    }),

  setAwaitingDecision: (awaiting) => set({ awaitingDecision: awaiting }),

  setWalkAwayThreshold: (threshold) => set({ walkAwayThreshold: threshold }),

  setSetupParams: (params) =>
    set({
      playerName: params.playerName,
      clubName: params.clubName,
      budgetEur: params.budgetEur,
      priorities: params.priorities,
      walkAwayThreshold: params.walkAwayThreshold,
    }),

  submitDecision: async (action, termSheet?) => {
    const { requestId, addLog, addRound, userSide, currentRound } = get();
    if (!requestId) return;

    addLog(`User decision: ${action}`);
    set({ awaitingDecision: false, warRoomResults: null });

    // Reset war room agents for next round
    set({
      agents: DEFAULT_AGENTS.map((a) => ({ ...a })),
    });

    try {
      const response = await fetch(`/api/backend/decide/${requestId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          term_sheet: termSheet || null,
        }),
      });

      if (!response.ok) {
        const err = await response.text();
        throw new Error(`Decision failed: ${err}`);
      }

      // If user accepted or walked away, add a round entry
      if (action === "ACCEPT" || action === "WALK_AWAY") {
        addRound({
          round_number: currentRound,
          side: userSide || "club",
          action,
          term_sheet: termSheet || null,
          reasoning: action === "ACCEPT" ? "User accepted the offer" : "User walked away from negotiation",
          constraint_violations: [],
          timestamp: new Date().toISOString(),
        });
      }

      addLog(`Decision submitted: ${action}`);
    } catch (error: any) {
      addLog(`Decision error: ${error.message}`);
      throw error;
    }
  },

  getActiveAgents: () => get().agents.filter((a) => a.status === "active"),

  getCompletedAgents: () => get().agents.filter((a) => a.status === "complete"),

  getLatestOffer: () => {
    const { rounds } = get();
    return rounds.length > 0 ? rounds[rounds.length - 1] : null;
  },

  getSalaryGap: () => {
    const { rounds } = get();
    const clubOffers = rounds.filter((r) => r.side === "club" && r.term_sheet);
    const playerOffers = rounds.filter(
      (r) => r.side === "player" && r.term_sheet
    );
    if (clubOffers.length === 0 || playerOffers.length === 0) return 0;
    const latestClub =
      clubOffers[clubOffers.length - 1].term_sheet?.base_salary_eur ?? 0;
    const latestPlayer =
      playerOffers[playerOffers.length - 1].term_sheet?.base_salary_eur ?? 0;
    if (latestPlayer === 0) return 0;
    return Math.abs(latestClub - latestPlayer) / latestPlayer;
  },

  getOpponentSide: () => {
    const { userSide } = get();
    return userSide === "club" ? "player" : "club";
  },
}));
