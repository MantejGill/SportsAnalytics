export interface TermSheet {
  player_name: string;
  position: string;
  base_salary_eur: number;
  signing_bonus_eur: number;
  performance_bonus_eur: number;
  contract_years: number;
  option_year: boolean;
  release_clause_eur: number;
  total_value_eur: number;
  image_rights_pct: number;
  no_trade_clause: boolean;
}

export interface NegotiationRound {
  round_number: number;
  side: "club" | "player";
  action: "PROPOSE" | "COUNTER" | "ACCEPT" | "WALK_AWAY";
  term_sheet: TermSheet | null;
  reasoning: string;
  constraint_violations: string[];
  timestamp: string;
}

export interface Comparable {
  player_name: string;
  position: string;
  salary_eur: number;
  club: string;
}

export interface MarketContext {
  predicted_value_eur: number;
  p25_eur: number;
  median_eur: number;
  p75_eur: number;
  comparables: Comparable[];
  salary_range?: {
    low_eur: number;
    mid_eur: number;
    high_eur: number;
    basis?: string;
  };
}

export interface PlayerProfile {
  name: string;
  age: number;
  position: string;
  current_club: string;
  stats: Record<string, number | string>;
}

export interface ClubConstraints {
  budget_eur: number;
  max_years: number;
  priorities: string[];
}

export type NegotiationStatus =
  | "idle"
  | "negotiating"
  | "accepted"
  | "walked_away"
  | "max_rounds";

export interface NegotiationState {
  player_profile: PlayerProfile | null;
  club_constraints: ClubConstraints | null;
  player_priorities: string[];
  market_context: MarketContext | null;
  rounds: NegotiationRound[];
  current_round: number;
  max_rounds: number;
  status: NegotiationStatus;
  active_agent: string | null;
  logs: string[];
}

export type AgentStatus = "idle" | "active" | "complete" | "error";

export interface AgentInfo {
  id: string;
  name: string;
  status: AgentStatus;
  description: string;
}

export interface NegotiationEvent {
  type: string;
  data: any;
  timestamp: string;
}

// --- War Room types ---

export type UserSide = "club" | "player";

export interface WarRoomComparables {
  analysis: string;
  similar_players: Array<{ name: string; salary: number; club: string }>;
}

export interface WarRoomOfferAnalysis {
  analysis: string;
  percentile: number;
  breakdown: Record<string, string>;
}

export interface WarRoomClauseRisk {
  analysis: string;
  risks: string[];
  missing_protections: string[];
}

export interface WarRoomStrategy {
  analysis: string;
  recommended_action: string;
  batna: number;
  zopa: [number, number];
}

export interface WarRoomFactCheck {
  analysis: string;
  verified: boolean;
  issues: string[];
}

export interface WarRoomResults {
  comparables: WarRoomComparables;
  offer_analysis: WarRoomOfferAnalysis;
  clause_risk: WarRoomClauseRisk;
  strategy: WarRoomStrategy;
  fact_check: WarRoomFactCheck;
  recommended_action: "ACCEPT" | "COUNTER" | "WALK_AWAY";
  recommended_counter: TermSheet | null;
  reasoning: string;
}

export type DecisionAction = "ACCEPT" | "COUNTER" | "WALK_AWAY";
