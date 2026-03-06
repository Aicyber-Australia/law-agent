export type Conversation = {
  id: string;
  title: string;
  ui_mode: "chat" | "analysis";
  legal_topic: string;
  user_state?: string | null;
  status: "active" | "archived" | "deleted";
  last_message_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  metadata?: Record<string, unknown>;
  created_at: string;
};

export type BriefSummary = {
  id: string;
  version: number;
  status: "generated" | "failed" | "deleted";
  created_at?: string;
  generated_at?: string;
  pdf_storage_path?: string | null;
};

export type DocumentRef = {
  document_id: string;
  conversation_id?: string | null;
  filename: string;
  mime_type?: string | null;
  file_size_bytes?: number;
  parsing_status?: string;
  document_url: string;
};
