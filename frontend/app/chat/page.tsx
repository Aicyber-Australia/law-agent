import { randomUUID } from "crypto";
import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";
import { BACKEND_URL } from "@/lib/backend";

export default async function ChatEntryPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    redirect("/login");
  }

  let conversationId = randomUUID();

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

  redirect(`/chat/${conversationId}`);
}
