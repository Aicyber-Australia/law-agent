import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { createClient } from "@/lib/supabase/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const serviceAdapter = new ExperimentalEmptyAdapter();

export const POST = async (req: NextRequest) => {
  // Extract auth session from cookies
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  // Create runtime with auth headers forwarded to backend
  const copilotRuntime = new CopilotRuntime({
    agents: {
      auslaw_agent: new HttpAgent({
        url: `${BACKEND_URL}/copilotkit`,
        headers: session
          ? { Authorization: `Bearer ${session.access_token}` }
          : {},
      }),
    },
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime: copilotRuntime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
