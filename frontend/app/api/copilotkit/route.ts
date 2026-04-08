import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import OpenAI from "openai";
import { NextRequest } from "next/server";

const runtime = new CopilotRuntime();

export const POST = async (req: NextRequest) => {
  try {
    const openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY || "",
    });

    const serviceAdapter = new OpenAIAdapter({
      openai: openai as any,
      model: "gpt-4o-mini",
      keepSystemRole: true,
      disableParallelToolCalls: false,
    });

    const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
      runtime,
      serviceAdapter,
      endpoint: "/api/copilotkit",
    });

    return handleRequest(req);
  } catch (error) {
    console.error("CopilotKit error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
};
