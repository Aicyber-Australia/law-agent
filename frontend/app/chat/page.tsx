import { randomUUID } from "crypto";
import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";
import { BACKEND_URL } from "@/lib/backend";

export default async function ChatEntryPage({
  searchParams,
}: {
  searchParams: { [key: string]: string | string[] | undefined };
}) {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  let conversationId = randomUUID();

  if (session?.access_token) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/conversations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          title: "New Conversation",
        }),
        cache: "no-store",
      });

      if (response.ok) {
        const payload = await response.json();
        conversationId = payload.conversation_id || payload.thread_id || conversationId;
      }
    } catch {
      // Fall back to local UUID; thread can still initialize in CopilotKit.
    }
  }

  const authParam = searchParams.auth;
  const authRequired =
    authParam === "required" || (Array.isArray(authParam) && authParam[0] === "required");
  const suffix = authRequired ? "?auth=required" : "";

  redirect(`/chat/${conversationId}${suffix}`);
}
