import type { Metadata } from "next";
import { redirect } from "next/navigation";

import AccountPageClient from "./AccountPageClient";
import { createClient } from "@/lib/supabase/server";
import { BACKEND_URL } from "@/lib/backend";
import type {
  AccountUserView,
  Conversation,
  ConversationListResponse,
} from "@/lib/api-types";

const PAGE_SIZE = 20;

export const metadata: Metadata = {
  title: "Account",
  robots: {
    index: false,
    follow: false,
  },
};

export default async function AccountPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  let initialConversations: Conversation[] = [];
  let initialHasMore = false;
  let initialError: string | null = null;

  try {
    const response = await fetch(
      `${BACKEND_URL}/api/v1/conversations?limit=${PAGE_SIZE}&offset=0`,
      {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
        cache: "no-store",
      }
    );

    if (!response.ok) {
      throw new Error("Failed to load conversations");
    }

    const payload = (await response.json()) as ConversationListResponse;
    initialConversations = Array.isArray(payload.items) ? payload.items : [];
    initialHasMore = initialConversations.length === PAGE_SIZE;
  } catch {
    initialError = "Could not load conversation history right now.";
  }

  const initialUser: AccountUserView = {
    fullName: String(user.user_metadata?.full_name || "Not set"),
    email: user.email || "Not set",
    userId: user.id,
    createdAt: user.created_at || null,
  };

  return (
    <AccountPageClient
      initialUser={initialUser}
      initialConversations={initialConversations}
      initialHasMore={initialHasMore}
      initialError={initialError}
    />
  );
}
