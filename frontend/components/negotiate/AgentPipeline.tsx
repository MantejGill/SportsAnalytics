"use client";

import React from "react";
import { motion } from "framer-motion";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import AgentCard from "./AgentCard";
import { ArrowRight } from "lucide-react";

export default function AgentPipeline() {
  const agents = useNegotiationStore((s) => s.agents);

  return (
    <div className="w-full overflow-x-auto">
      <div className="flex items-center gap-2 p-4">
        <span className="mr-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          War Room
        </span>
        {agents.map((agent, index) => (
          <React.Fragment key={agent.id}>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <AgentCard agent={agent} />
            </motion.div>
            {index < agents.length - 1 && (
              <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
