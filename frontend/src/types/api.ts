export type Lead = {
  id?: string;
  status?: "new" | "needs_info" | "quoted" | "handoff_required" | "closed";
  service_need?: string;
  phone?: string;
  address?: string;
  preferred_time?: string;
  urgency?: string;
  quote?: string | Record<string, unknown>;
  updated_at?: string;
};

export type ChatHistoryItem = {
  role: "assistant" | "user";
  content: string;
};

export type ChatResponse = {
  assistant_reply: string;
  lead?: Lead;
  missing_fields?: string[];
  quote?: string | Record<string, unknown>;
  handoff_required?: boolean;
  retrieved_context?: string;
  retrieved_sources?: string[];
};
