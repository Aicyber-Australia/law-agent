"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Archive,
  ArrowLeft,
  Calendar,
  ExternalLink,
  Fingerprint,
  Loader2,
  LogOut,
  Mail,
  Trash2,
  User,
} from "lucide-react";

import { createClient } from "@/lib/supabase/client";
import { BACKEND_URL } from "@/lib/backend";
import type {
  AccountUserView,
  Conversation,
  ConversationListResponse,
} from "@/lib/api-types";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const PAGE_SIZE = 20;

type ConversationFilter = "all" | "active" | "archived";
type ActionState =
  | {
      conversationId: string;
      type: "archiving" | "deleting";
    }
  | null;

type AccountPageClientProps = {
  initialUser: AccountUserView;
  initialConversations: Conversation[];
  initialHasMore: boolean;
  initialError: string | null;
};

export default function AccountPageClient({
  initialUser,
  initialConversations,
  initialHasMore,
  initialError,
}: AccountPageClientProps) {
  const router = useRouter();

  const [filter, setFilter] = useState<ConversationFilter>("all");
  const [conversations, setConversations] = useState<Conversation[]>(
    initialConversations
  );
  const [hasMore, setHasMore] = useState(initialHasMore);
  const [nextOffset, setNextOffset] = useState(initialConversations.length);
  const [loadingMore, setLoadingMore] = useState(false);
  const [actionState, setActionState] = useState<ActionState>(null);
  const [error, setError] = useState<string | null>(initialError);
  const [signingOut, setSigningOut] = useState(false);

  const filteredConversations = useMemo(() => {
    if (filter === "all") return conversations;
    return conversations.filter((conversation) => conversation.status === filter);
  }, [conversations, filter]);

  const backendRequest = async (path: string, init?: RequestInit) => {
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.access_token) {
      throw new Error("Authentication required");
    }

    return fetch(`${BACKEND_URL}${path}`, {
      ...init,
      headers: {
        ...(init?.headers || {}),
        Authorization: `Bearer ${session.access_token}`,
      },
    });
  };

  const fetchConversationPage = async (offset: number) => {
    const response = await backendRequest(
      `/api/v1/conversations?limit=${PAGE_SIZE}&offset=${offset}`
    );
    if (!response.ok) {
      throw new Error("Unable to load conversations");
    }
    const payload = (await response.json()) as ConversationListResponse;
    return Array.isArray(payload.items) ? payload.items : [];
  };

  const refreshFirstPage = async () => {
    const page = await fetchConversationPage(0);
    setConversations(page);
    setNextOffset(page.length);
    setHasMore(page.length === PAGE_SIZE);
  };

  const handleLoadMore = async () => {
    setError(null);
    setLoadingMore(true);
    try {
      const page = await fetchConversationPage(nextOffset);
      setConversations((prev) => [...prev, ...page]);
      setNextOffset((prev) => prev + page.length);
      setHasMore(page.length === PAGE_SIZE);
    } catch {
      setError("Could not load more conversations right now.");
    } finally {
      setLoadingMore(false);
    }
  };

  const handleArchive = async (conversationId: string) => {
    setError(null);
    setActionState({ conversationId, type: "archiving" });
    try {
      const response = await backendRequest(
        `/api/v1/conversations/${conversationId}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ status: "archived" }),
        }
      );
      if (!response.ok) {
        throw new Error("Failed to archive conversation");
      }
      await refreshFirstPage();
    } catch {
      setError("Could not archive that conversation.");
    } finally {
      setActionState(null);
    }
  };

  const handleDelete = async (conversationId: string) => {
    const shouldDelete = window.confirm(
      "Delete this conversation? This action cannot be undone."
    );
    if (!shouldDelete) return;

    setError(null);
    setActionState({ conversationId, type: "deleting" });

    try {
      const response = await backendRequest(
        `/api/v1/conversations/${conversationId}`,
        {
          method: "DELETE",
        }
      );
      if (!response.ok) {
        throw new Error("Failed to delete conversation");
      }
      await refreshFirstPage();
    } catch {
      setError("Could not delete that conversation.");
    } finally {
      setActionState(null);
    }
  };

  const handleSignOut = async () => {
    setSigningOut(true);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  };

  const formatDate = (timestamp?: string | null) => {
    if (!timestamp) return "Not available";
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return "Not available";
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const formatLegalTopic = (topic?: string) => {
    const value = (topic || "general").replaceAll("_", " ");
    return value
      .split(" ")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <Image src="/logo.svg" alt="AusLaw AI" width={72} height={72} />
            <span className="text-xl font-semibold text-slate-900 tracking-tight">
              AusLaw AI
            </span>
          </Link>
          <div className="flex items-center gap-2">
            <Button asChild variant="outline" className="cursor-pointer">
              <Link href="/chat">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Chat
              </Link>
            </Button>
            <Button
              onClick={handleSignOut}
              variant="ghost"
              className="cursor-pointer text-red-600 hover:text-red-700"
              disabled={signingOut}
            >
              {signingOut ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <LogOut className="mr-2 h-4 w-4" />
              )}
              Log out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 lg:py-8">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-2xl tracking-tight">Account</CardTitle>
            <CardDescription>
              Your profile details and conversation history.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
                <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <User className="h-4 w-4" />
                  Full Name
                </p>
                <p className="text-sm font-medium text-slate-900">
                  {initialUser.fullName}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
                <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <Mail className="h-4 w-4" />
                  Email
                </p>
                <p className="text-sm font-medium text-slate-900 break-words">
                  {initialUser.email}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
                <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <Fingerprint className="h-4 w-4" />
                  User ID
                </p>
                <p className="text-sm font-mono text-slate-800 break-all">
                  {initialUser.userId}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
                <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <Calendar className="h-4 w-4" />
                  Account Created
                </p>
                <p className="text-sm font-medium text-slate-900">
                  {formatDate(initialUser.createdAt)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="space-y-4">
            <div>
              <CardTitle className="text-xl tracking-tight">
                Conversation History
              </CardTitle>
              <CardDescription>
                Open, archive, or delete your previous conversations.
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <FilterButton
                active={filter === "all"}
                onClick={() => setFilter("all")}
                label={`All (${conversations.length})`}
              />
              <FilterButton
                active={filter === "active"}
                onClick={() => setFilter("active")}
                label={`Active (${conversations.filter((c) => c.status === "active").length})`}
              />
              <FilterButton
                active={filter === "archived"}
                onClick={() => setFilter("archived")}
                label={`Archived (${conversations.filter((c) => c.status === "archived").length})`}
              />
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive" className="border-red-300 bg-red-50">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Could not complete request</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {filteredConversations.length === 0 && (
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
                <p className="text-sm text-slate-600">
                  {conversations.length === 0
                    ? "No conversations yet."
                    : `No ${filter} conversations right now.`}
                </p>
              </div>
            )}

            {filteredConversations.map((conversation) => {
              const isBusy = actionState?.conversationId === conversation.id;
              const isDeleting = isBusy && actionState?.type === "deleting";
              const isArchiving = isBusy && actionState?.type === "archiving";
              return (
                <div
                  key={conversation.id}
                  className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-semibold text-slate-900">
                        {conversation.title || "Untitled Conversation"}
                      </p>
                      <Badge
                        variant="secondary"
                        className={
                          conversation.status === "active"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-slate-100 text-slate-700 border border-slate-200"
                        }
                      >
                        {conversation.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-600">
                      Topic: {formatLegalTopic(conversation.legal_topic)}
                    </p>
                    <p className="text-xs text-slate-500">
                      Last activity:{" "}
                      {formatDate(
                        conversation.last_message_at || conversation.created_at
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => router.push(`/chat/${conversation.id}`)}
                      className="cursor-pointer"
                      disabled={isBusy}
                    >
                      <ExternalLink className="mr-2 h-4 w-4" />
                      Open
                    </Button>
                    {conversation.status === "active" && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleArchive(conversation.id)}
                        className="cursor-pointer"
                        disabled={isBusy}
                      >
                        {isArchiving ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Archive className="mr-2 h-4 w-4" />
                        )}
                        Archive
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(conversation.id)}
                      className="cursor-pointer text-red-600 hover:text-red-700"
                      disabled={isBusy}
                    >
                      {isDeleting ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="mr-2 h-4 w-4" />
                      )}
                      Delete
                    </Button>
                  </div>
                </div>
              );
            })}

            {hasMore && (
              <div className="flex justify-center">
                <Button
                  variant="outline"
                  onClick={handleLoadMore}
                  className="cursor-pointer"
                  disabled={loadingMore}
                >
                  {loadingMore ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    "Load More"
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function FilterButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <Button
      type="button"
      onClick={onClick}
      variant={active ? "default" : "outline"}
      className="cursor-pointer"
      size="sm"
    >
      {label}
    </Button>
  );
}
