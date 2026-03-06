"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";
import {
  useCopilotReadable,
  useCopilotChat,
  useCoAgent,
} from "@copilotkit/react-core";
import { TextMessage, MessageRole } from "@copilotkit/runtime-client-gql";
import { createClient } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";
import { StateSelector } from "../../components/StateSelector";
import { FileUpload } from "../../components/FileUpload";
import { ModeToggle } from "../../components/ModeToggle";
import { TopicSelector, type LegalTopic } from "../../components/TopicSelector";
import { useMode } from "../../contexts/ModeContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BACKEND_URL } from "@/lib/backend";
import type { Conversation } from "@/lib/api-types";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import Image from "next/image";
import {
  FileCheck,
  X,
  Menu,
  ArrowLeft,
  FileText,
  Download,
  Archive,
  RotateCcw,
  Trash2,
  MoreHorizontal,
  Home,
  Briefcase,
  Plus,
  Users,
  RefreshCw,
  LogOut,
  Shield,
  DollarSign,
  ArrowUpCircle,
  Car,
} from "lucide-react";

type ConversationSummary = Pick<Conversation, "id" | "title" | "status" | "legal_topic" | "last_message_at">;

type UploadedDocument = {
  documentId: string;
  url: string;
  filename: string;
};

export default function ChatPageClient({ conversationId }: { conversationId: string }) {
  const router = useRouter();
  const [userState, setUserState] = useState<string | null>(null);
  const [uploadedDocument, setUploadedDocument] = useState<UploadedDocument | null>(null);
  const [legalTopic, setLegalTopic] = useState<LegalTopic>("general");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [latestBriefId, setLatestBriefId] = useState<string | null>(null);
  const [downloadingBrief, setDownloadingBrief] = useState(false);
  const [conversationStarted, setConversationStarted] = useState(false);

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

  const loadConversations = async () => {
    try {
      const response = await backendRequest("/api/v1/conversations?limit=30&offset=0");
      if (!response.ok) return;
      const payload = await response.json();
      setConversations(payload.items || []);
    } catch {
      // Non-fatal in UI.
    }
  };

  const loadConversationContext = async () => {
    try {
      const response = await backendRequest(
        `/api/v1/conversations/${conversationId}?message_limit=20`
      );
      if (!response.ok) return;
      const payload = await response.json();
      setUserState(payload.user_state ?? null);
      setLegalTopic(payload.legal_topic ?? "general");
      setLatestBriefId(payload.latest_brief?.id || null);
      setConversationStarted(Array.isArray(payload.messages) && payload.messages.length > 0);
      setUploadedDocument(null);
    } catch {
      // Non-fatal in UI.
    }
  };

  // Fetch current user and conversation context
  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => setUser(user));
    loadConversations();
    loadConversationContext();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  };

  // Get user initials for avatar
  const getUserInitials = () => {
    if (!user) return "?";
    const name = user.user_metadata?.full_name || user.email || "";
    if (user.user_metadata?.full_name) {
      return name
        .split(" ")
        .map((n: string) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    }
    return (user.email?.[0] || "?").toUpperCase();
  };

  // Get current mode from context
  const { mode } = useMode();

  useCopilotReadable({
    description: "Authenticated user id",
    value: user?.id || "unknown",
  });

  useCopilotReadable({
    description: "Conversation/thread id",
    value: conversationId,
  });

  // Share user's state/territory with the Copilot agent
  useCopilotReadable({
    description: "The user's Australian state/territory for legal queries",
    value: userState
      ? `User is in ${userState}. Use state="${userState}" for lookup_law, find_lawyer, and generate_checklist tools.`
      : "User has not selected their state yet.",
  });

  // Share uploaded document URL with the Copilot agent
  useCopilotReadable({
    description: "Uploaded document URL for analysis",
    value: uploadedDocument
      ? `The user has uploaded a document named "${uploadedDocument.filename}" (document id: ${uploadedDocument.documentId}). The document URL is: ${uploadedDocument.url}\n\nWhen the user asks to analyze this document, use the analyze_document tool with document_url="${uploadedDocument.url}". Automatically detect the document type (lease, contract, visa, or general) based on the filename or user's request.`
      : "No document uploaded yet.",
  });

  // Share UI mode with the Copilot agent
  useCopilotReadable({
    description: "The UI mode the user has selected",
    value:
      mode === "analysis"
        ? `User is in ANALYSIS MODE. This means they want a thorough consultation like talking to a lawyer. Guide them through understanding their situation first, then explain the relevant law, and finally offer options and strategy when they ask or when it's natural.`
        : `User is in CHAT MODE. This is casual Q&A mode for quick legal questions. Be helpful and conversational.`,
  });

  // Share legal topic with the Copilot agent
  useCopilotReadable({
    description: "The legal topic the user has selected",
    value:
      legalTopic === "parking_ticket"
        ? `User has selected PARKING TICKET topic. They want help fighting a parking fine, traffic ticket, speeding fine, or similar infringement notice. Use the parking ticket playbook to guide them.`
        : legalTopic === "insurance_claim"
        ? `User has selected INSURANCE CLAIM topic. They want help with an insurance claim dispute, denial, underpayment, or delay. Use the insurance claim playbook to guide them.`
        : `User has not selected a specific legal topic. Provide general legal assistance.`,
  });

  const handleFileUploaded = (document: UploadedDocument) => {
    setUploadedDocument(document);
  };

  const clearDocument = () => {
    setUploadedDocument(null);
  };

  // Access agent state for quick replies
  const { state: agentState } = useCoAgent<{
    quick_replies?: string[];
    suggest_brief?: boolean;
    latest_brief_id?: string;
  }>({
    name: "auslaw_agent",
  });

  // Quick replies from agent state
  const quickReplies = agentState?.quick_replies;

  useEffect(() => {
    if (agentState?.latest_brief_id) {
      setLatestBriefId(agentState.latest_brief_id);
      loadConversations();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentState?.latest_brief_id]);

  // Auto-continue conversation when user selects a state after being prompted
  const { appendMessage } = useCopilotChat();
  const prevUserState = useRef(userState);
  const userSentMessage = useRef(false);

  useEffect(() => {
    if (prevUserState.current === null && userState !== null && userSentMessage.current) {
      appendMessage(
        new TextMessage({
          role: MessageRole.User,
          content: `I've selected ${userState} as my state.`,
        })
      );
    }
    prevUserState.current = userState;
  }, [userState, appendMessage]);

  const handleOpenConversation = (id: string) => {
    router.push(`/chat/${id}`);
    setSidebarOpen(false);
  };

  const handleArchiveConversation = async (id: string) => {
    try {
      await backendRequest(`/api/v1/conversations/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ status: "archived" }),
      });
      await loadConversations();
    } catch {
      // Non-fatal in UI.
    }
  };

  const handleResumeConversation = async (id: string) => {
    try {
      await backendRequest(`/api/v1/conversations/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ status: "active" }),
      });
      await loadConversations();
      handleOpenConversation(id);
    } catch {
      // Non-fatal in UI.
    }
  };

  const handleDeleteConversation = async (id: string) => {
    const shouldDelete = window.confirm(
      "Delete this conversation? This will remove it from your active history."
    );
    if (!shouldDelete) return;

    try {
      const response = await backendRequest(`/api/v1/conversations/${id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete conversation");
      }

      await loadConversations();
      if (id === conversationId) {
        router.push("/chat");
      }
    } catch {
      // Non-fatal in UI.
    }
  };

  const resolveLatestBriefId = async () => {
    if (latestBriefId) return latestBriefId;
    try {
      const response = await backendRequest(
        `/api/v1/conversations/${conversationId}?message_limit=1`
      );
      if (!response.ok) return null;
      const payload = await response.json();
      const resolved = payload?.latest_brief?.id || null;
      if (resolved) setLatestBriefId(resolved);
      return resolved;
    } catch {
      return null;
    }
  };

  const handleDownloadBrief = async () => {
    setDownloadingBrief(true);
    try {
      const briefId = await resolveLatestBriefId();
      if (!briefId) {
        alert(
          "No saved brief found yet. If the assistant asked follow-up questions, answer them first, then generate again."
        );
        return;
      }

      const response = await backendRequest(`/api/v1/briefs/${briefId}/pdf`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Failed to generate PDF");
      }
      const payload = await response.json();
      if (payload?.download_url) {
        window.open(payload.download_url, "_blank", "noopener,noreferrer");
      }
    } catch {
      // Non-fatal in UI.
    } finally {
      setDownloadingBrief(false);
    }
  };

  // Reset conversation handler - create and redirect to fresh conversation
  const handleNewConversation = () => {
    router.push("/chat");
  };

  useEffect(() => {
    if (!user) return;
    const persistMetadata = async () => {
      try {
        await backendRequest(`/api/v1/conversations/${conversationId}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ui_mode: mode,
            legal_topic: legalTopic,
            user_state: userState,
          }),
        });
      } catch {
        // Non-fatal in UI.
      }
    };
    persistMetadata();
  }, [conversationId, legalTopic, mode, user, userState]);

  // Dynamic initial message based on selected state and topic
  const getInitialMessage = () => {
    if (legalTopic === "insurance_claim") {
      if (userState) {
        return `G'day! I'm here to help you with your insurance claim in **${userState}**.\n\nI can help with:\n• Denied insurance claims\n• Underpaid or delayed claims\n• Motor vehicle insurance disputes\n• Home & contents insurance issues\n• Escalating to AFCA (free)\n\nWhat's happening with your insurance claim?`;
      }
      return "G'day! I'm here to help you with your insurance claim. Please select your state/territory from the sidebar first — some consumer protection options vary by state.";
    }
    if (legalTopic === "parking_ticket") {
      if (userState) {
        return `G'day! I'm here to help you challenge a fine or ticket in **${userState}**.\n\nI can help with:\n• Parking fines\n• Speeding tickets\n• Red light camera fines\n• Public transport fines\n• Council infringement notices\n\nWhat kind of ticket or fine are you dealing with?`;
      }
      return "G'day! I'm here to help you fight a fine or ticket. Please select your state/territory from the sidebar first — the appeal process varies by state.";
    }
    if (userState) {
      return `G'day! I'm your AusLaw AI assistant. I see you're in **${userState}**.\n\nI can help you with:\n• Understanding your legal rights\n• Step-by-step guides for legal procedures\n• Finding a qualified lawyer\n\nHow can I assist you today?`;
    }
    return "G'day! I'm your AusLaw AI assistant. Please select your state/territory from the sidebar so I can provide jurisdiction-specific guidance.";
  };

  const formatConversationTime = (timestamp?: string | null) => {
    if (!timestamp) return "No activity";
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return "No activity";
    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  };

  const currentConversationTitle =
    conversations.find((conversation) => conversation.id === conversationId)?.title ||
    "Conversation";

  // Sidebar content component
  const SidebarContent = () => (
    <div className="flex flex-col h-full gap-6">
      {/* Mode Toggle */}
      <ModeToggle />

      {/* Legal Topic Selector */}
      <TopicSelector
        selectedTopic={legalTopic}
        onTopicChange={setLegalTopic}
      />

      {/* Recent Conversations */}
      <div className="space-y-2">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Conversations
        </div>
        <div className="max-h-44 overflow-y-auto space-y-1 pr-1">
          {conversations.length === 0 && (
            <p className="text-sm text-slate-500">No conversations yet.</p>
          )}
          {conversations.map((conversation) => {
            const isActiveConversation = conversation.id === conversationId;
            return (
              <div
                key={conversation.id}
                className={`flex items-center gap-2 rounded-lg border px-2.5 py-2 ${
                  isActiveConversation
                    ? "border-primary/40 bg-primary/5"
                    : "border-slate-200 bg-white"
                }`}
              >
                <button
                  type="button"
                  onClick={() => handleOpenConversation(conversation.id)}
                  className="flex-1 min-w-0 text-left"
                >
                  <p className="truncate text-sm font-medium text-slate-800">
                    {conversation.title || "Untitled Conversation"}
                  </p>
                  <p className="text-xs text-slate-500">
                    {conversation.status === "archived" ? "Archived" : "Active"} ·{" "}
                    {formatConversationTime(conversation.last_message_at)}
                  </p>
                </button>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-slate-500"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-44">
                    <DropdownMenuItem onClick={() => handleOpenConversation(conversation.id)}>
                      Open
                    </DropdownMenuItem>
                    {conversation.status === "archived" ? (
                      <DropdownMenuItem onClick={() => handleResumeConversation(conversation.id)}>
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Resume
                      </DropdownMenuItem>
                    ) : (
                      <DropdownMenuItem onClick={() => handleArchiveConversation(conversation.id)}>
                        <Archive className="mr-2 h-4 w-4" />
                        Archive
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => handleDeleteConversation(conversation.id)}
                      className="text-red-600 focus:text-red-600"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            );
          })}
        </div>
      </div>

      {/* Divider */}
      <div className="h-px bg-slate-200" />

      {/* Location Section */}
      <div className="space-y-3">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Your Jurisdiction
        </div>
        <StateSelector
          selectedState={userState}
          onStateChange={setUserState}
        />
      </div>

      {/* Document Upload Section */}
      <div className="space-y-3">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Document Analysis
        </div>
        <FileUpload
          conversationId={conversationId}
          onFileUploaded={handleFileUploaded}
        />
        {uploadedDocument && (
          <Badge
            variant="secondary"
            className="gap-2 h-10 px-3 bg-emerald-50 text-emerald-700 border border-emerald-200 w-full justify-start text-sm"
          >
            <FileCheck className="h-4 w-4 text-emerald-600 shrink-0" />
            <span className="truncate flex-1 text-left">
              {uploadedDocument.filename}
            </span>
            <button
              onClick={clearDocument}
              className="hover:text-red-600 transition-colors cursor-pointer ml-auto"
              aria-label="Remove document"
            >
              <X className="h-4 w-4" />
            </button>
          </Badge>
        )}
        <p className="text-sm text-slate-500">
          Upload leases, contracts, or legal documents for AI analysis.
        </p>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Generate Brief Button */}
      <GenerateBriefButton onClose={() => setSidebarOpen(false)} />

      <Button
        onClick={handleDownloadBrief}
        variant="outline"
        disabled={downloadingBrief}
        className="w-full cursor-pointer gap-2 h-10 text-sm font-medium border-slate-200 hover:bg-slate-50 hover:border-slate-300 transition-all disabled:cursor-not-allowed"
      >
        <Download className="h-4 w-4" />
        {downloadingBrief ? "Preparing PDF..." : "Download Latest PDF"}
      </Button>

      {/* New Conversation Button */}
      <Button
        onClick={handleNewConversation}
        variant="outline"
        className="w-full cursor-pointer gap-2 h-10 text-sm font-medium border-slate-200 hover:bg-slate-50 hover:border-slate-300 transition-all"
      >
        <Plus className="h-4 w-4" />
        New Conversation
      </Button>

      {/* Disclaimer */}
      <div className="p-3 bg-amber-50/80 border border-amber-200/60 rounded-lg">
        <p className="text-xs text-amber-800 leading-relaxed">
          <span className="font-medium">Disclaimer:</span> This tool provides
          general legal information only, not legal advice. Always consult a
          qualified solicitor for specific matters.
        </p>
      </div>
    </div>
  );

  return (
    <div className="flex h-dvh bg-slate-50 chat-page-container">
      {/* Mobile Header */}
      <header className="fixed top-0 left-0 right-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200/80 lg:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
              <SheetTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="cursor-pointer hover:bg-slate-100"
                  aria-label="Open menu"
                >
                  <Menu className="h-5 w-5 text-slate-600" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-80 p-5">
                <SheetHeader className="mb-6">
                  <SheetTitle className="flex items-center gap-2.5 text-lg">
                    <Image src="/logo.svg" alt="AusLaw AI" width={72} height={72} />
                    <span className="font-semibold">AusLaw AI</span>
                  </SheetTitle>
                </SheetHeader>
                <SidebarContent />
              </SheetContent>
            </Sheet>

            <div className="flex items-center gap-2">
              <Image src="/logo.svg" alt="AusLaw AI" width={80} height={80} />
              <span className="font-semibold text-slate-900">AusLaw AI</span>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="cursor-pointer rounded-full h-9 w-9">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
                    {getUserInitials()}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="font-normal">
                <p className="text-sm font-medium">{user?.user_metadata?.full_name || "Account"}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild className="cursor-pointer">
                <Link href="/">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Home
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleSignOut} className="cursor-pointer text-red-600 focus:text-red-600">
                <LogOut className="mr-2 h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex w-80 xl:w-[340px] flex-col border-r border-slate-200/80 bg-white">
        {/* Sidebar Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-100">
          <Link href="/" className="flex items-center gap-2.5 group">
            <Image src="/logo.svg" alt="AusLaw AI" width={80} height={80} />
            <span className="text-xl font-semibold text-slate-900 tracking-tight">
              AusLaw AI
            </span>
          </Link>
          <Link href="/">
            <Button
              variant="ghost"
              size="sm"
              className="text-slate-400 hover:text-slate-700 cursor-pointer"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
        </div>

        {/* Sidebar Body */}
        <div className="flex-1 p-5 overflow-y-auto">
          <SidebarContent />
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-gradient-to-b from-slate-50 to-white relative">
        {/* Chat Header */}
        <div className="hidden lg:flex items-center justify-between px-6 py-3 border-b border-slate-200/60 bg-white/80 backdrop-blur-sm">
          <span className="text-sm font-medium text-slate-600">
            {mode === "analysis" ? "Case Analysis" : "Legal Chat"} · {currentConversationTitle}
            {legalTopic !== "general" && (
              <span className="text-slate-400"> — {legalTopic === "parking_ticket" ? "Parking Ticket" : "Insurance Claim"}</span>
            )}
          </span>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="cursor-pointer rounded-full h-9 w-9">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
                    {getUserInitials()}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="font-normal">
                <p className="text-sm font-medium">{user?.user_metadata?.full_name || "Account"}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild className="cursor-pointer">
                <Link href="/">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Home
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleSignOut} className="cursor-pointer text-red-600 focus:text-red-600">
                <LogOut className="mr-2 h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Add top padding on mobile for fixed header */}
        <div className="flex-1 pt-14 lg:pt-0 flex flex-col min-h-0 overflow-hidden">
          {/* Welcome Section - shown only when conversation hasn't started */}
          {!conversationStarted && (
            <WelcomeSection legalTopic={legalTopic} onTopicClick={() => { userSentMessage.current = true; setConversationStarted(true); }} />
          )}

          {/* Chat area */}
          <CopilotChat
            className="flex-1 min-h-0"
            labels={{
              title: `${mode === "analysis" ? "Case Analysis" : "Legal Chat"}${legalTopic === "parking_ticket" ? " — Parking Ticket" : legalTopic === "insurance_claim" ? " — Insurance Claim" : ""}`,
              initial: getInitialMessage(),
            }}
            onSubmitMessage={() => {
              userSentMessage.current = true;
              setConversationStarted(true);
            }}
          />
        </div>

        {/* Quick Replies - positioned above input, outside overflow container */}
        {quickReplies && quickReplies.length > 0 && (
          <div className="quick-replies-container">
            <QuickRepliesPanel replies={quickReplies} />
          </div>
        )}
      </main>
    </div>
  );
}

/**
 * WelcomeSection - Welcome header with topic pill buttons
 */
function WelcomeSection({ legalTopic, onTopicClick }: { legalTopic: LegalTopic; onTopicClick: () => void }) {
  const { appendMessage } = useCopilotChat();

  const generalTopics = [
    {
      icon: Home,
      label: "What are my tenant rights?",
      prompt: "What are my tenant rights?",
    },
    {
      icon: Briefcase,
      label: "Explain unfair dismissal laws",
      prompt: "Explain unfair dismissal laws",
    },
    {
      icon: Users,
      label: "Help with a family law dispute",
      prompt: "Help with a family law dispute",
    },
    {
      icon: RefreshCw,
      label: "What does Australian Consumer Law cover?",
      prompt: "What does Australian Consumer Law cover?",
    },
  ];

  const parkingTicketTopics = [
    {
      icon: Home,
      label: "I got a parking fine",
      prompt: "I got a parking fine, what are my options to challenge it?",
    },
    {
      icon: Briefcase,
      label: "Speeding ticket options",
      prompt: "I received a speeding ticket. What are my options to challenge it?",
    },
    {
      icon: Users,
      label: "Challenge a camera fine",
      prompt: "Can I challenge a red light camera fine?",
    },
    {
      icon: RefreshCw,
      label: "Missed payment deadline",
      prompt: "I missed the payment deadline on my fine. What can I do?",
    },
  ];

  const insuranceClaimTopics = [
    {
      icon: Shield,
      label: "My claim was denied",
      prompt: "My insurance claim was denied. What are my options to dispute this?",
    },
    {
      icon: DollarSign,
      label: "Insurer is underpaying",
      prompt: "My insurer is underpaying my claim. What can I do?",
    },
    {
      icon: ArrowUpCircle,
      label: "How do I escalate to AFCA?",
      prompt: "How do I escalate my insurance dispute to AFCA?",
    },
    {
      icon: Car,
      label: "Car accident insurance dispute",
      prompt: "I'm having a dispute with my car insurance after an accident. What are my rights?",
    },
  ];

  const topicPills: Record<string, typeof generalTopics> = {
    general: generalTopics,
    parking_ticket: parkingTicketTopics,
    insurance_claim: insuranceClaimTopics,
  };

  const topics = topicPills[legalTopic] || generalTopics;

  const handleTopicClick = async (prompt: string) => {
    onTopicClick(); // Hide welcome section immediately
    await appendMessage(
      new TextMessage({
        role: MessageRole.User,
        content: prompt,
      })
    );
  };

  return (
    <div className="flex flex-wrap justify-center gap-2 px-4 py-3">
      {topics.map((topic) => (
        <button
          key={topic.label}
          onClick={() => handleTopicClick(topic.prompt)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-full border border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300 transition-all duration-200 cursor-pointer group"
        >
          <topic.icon className="h-4 w-4 text-slate-400 group-hover:text-slate-600 transition-colors flex-shrink-0" />
          <span className="text-sm text-slate-600 group-hover:text-slate-900 transition-colors">
            {topic.label}
          </span>
        </button>
      ))}
    </div>
  );
}

/**
 * QuickRepliesPanel - Renders suggested quick reply buttons from agent state
 * Positioned above the input box
 */
function QuickRepliesPanel({ replies }: { replies: string[] }) {
  const { appendMessage } = useCopilotChat();

  const handleQuickReply = async (reply: string) => {
    await appendMessage(
      new TextMessage({
        role: MessageRole.User,
        content: reply,
      })
    );
  };

  return (
    <div className="quick-replies-panel">
      {replies.slice(0, 3).map((reply, index) => (
        <Button
          key={index}
          variant="outline"
          size="sm"
          className="text-sm text-slate-600 hover:text-slate-900 hover:bg-white hover:border-primary/30 border-slate-200 bg-white cursor-pointer transition-all rounded-full px-4"
          onClick={() => handleQuickReply(reply)}
        >
          {reply}
        </Button>
      ))}
    </div>
  );
}

/**
 * GenerateBriefButton - Triggers lawyer brief generation
 */
function GenerateBriefButton({ onClose }: { onClose?: () => void }) {
  const { appendMessage, isLoading } = useCopilotChat();

  const handleGenerateBrief = async () => {
    await appendMessage(
      new TextMessage({
        role: MessageRole.User,
        content:
          "[GENERATE_BRIEF] Please prepare a lawyer brief based on our conversation.",
      })
    );
    onClose?.();
  };

  return (
    <Button
      onClick={handleGenerateBrief}
      disabled={isLoading}
      className="w-full bg-primary hover:bg-primary/90 text-white cursor-pointer gap-2 h-10 text-sm font-medium shadow-sm shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
    >
      <FileText className="h-4 w-4" />
      Generate Lawyer Brief
    </Button>
  );
}
