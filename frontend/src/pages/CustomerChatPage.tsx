import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent } from "react";

import { ChatComposer } from "../components/chat/ChatComposer";
import { ChatMessageList } from "../components/chat/ChatMessageList";
import type { ChatMessage } from "../components/chat/ChatMessageList";
import { QuickPrompts } from "../components/chat/QuickPrompts";
import "../styles/customer-chat.css";

type Lead = Record<string, unknown>;

type ChatHistoryItem = {
  role: "assistant" | "user";
  content: string;
};

type ChatResponse = {
  assistant_reply: string;
  lead?: Lead;
  missing_fields?: string[];
  quote?: string | Record<string, unknown>;
  handoff_required?: boolean;
};

const welcomeText = "您好，我是安心到家 AI 服务顾问。";
const welcomeDetail = "需要保洁、维修，还是想先了解价格？";
const posterUrl = "/images/home-service-poster.png";
const heroVideoUrl = import.meta.env.VITE_HERO_VIDEO_URL as string | undefined;

function createMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
  };
}

export default function CustomerChatPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [typedWelcome, setTypedWelcome] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatHistoryItem[]>([]);
  const [currentLead, setCurrentLead] = useState<Lead>({});
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const [handoffRequired, setHandoffRequired] = useState(false);
  const [videoReady, setVideoReady] = useState(Boolean(heroVideoUrl));
  const hasConversation = messages.length > 0;

  useEffect(() => {
    let index = 0;
    const interval = window.setInterval(() => {
      index += 1;
      setTypedWelcome(welcomeText.slice(0, index));
      if (index >= welcomeText.length) {
        window.clearInterval(interval);
      }
    }, 58);

    return () => window.clearInterval(interval);
  }, []);

  const requestHistory = useMemo(
    () => chatHistory.map(({ role, content }) => ({ role, content })),
    [chatHistory],
  );

  function handleHeroPointerMove(event: MouseEvent<HTMLElement>) {
    const video = videoRef.current;
    if (!video || !video.duration || Number.isNaN(video.duration)) {
      return;
    }

    const bounds = event.currentTarget.getBoundingClientRect();
    const progress = Math.min(1, Math.max(0, (event.clientX - bounds.left) / bounds.width));
    video.currentTime = progress * video.duration;
  }

  async function sendMessage(message: string) {
    if (!message.trim() || isSending) {
      return;
    }

    const userMessage = createMessage("user", message);
    const nextHistory: ChatHistoryItem[] = [...requestHistory, { role: "user", content: message }];

    setMessages((previous) => [...previous, userMessage]);
    setChatHistory(nextHistory);
    setError("");
    setIsSending(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          current_lead: currentLead,
          chat_history: requestHistory,
        }),
      });

      if (!response.ok) {
        throw new Error(`咨询服务暂时不可用（${response.status}）`);
      }

      const payload = (await response.json()) as ChatResponse;
      const assistantReply =
        payload.assistant_reply?.trim() || "您的需求已收到，我会继续帮您登记。";

      setCurrentLead(payload.lead ?? currentLead);
      setHandoffRequired(Boolean(payload.handoff_required));
      setMessages((previous) => [...previous, createMessage("assistant", assistantReply)]);
      setChatHistory([...nextHistory, { role: "assistant", content: assistantReply }]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "发送失败，请稍后再试。");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="customer-chat-page" onMouseMove={handleHeroPointerMove}>
      <div className="hero-media" aria-hidden="true">
        {heroVideoUrl && videoReady ? (
          <video
            muted
            onError={() => setVideoReady(false)}
            playsInline
            poster={posterUrl}
            preload="metadata"
            ref={videoRef}
            src={heroVideoUrl}
          />
        ) : null}
      </div>
      <div className="hero-shade" aria-hidden="true" />

      <header className="customer-header">
        <a className="brand-lockup" href="/chat">
          <span className="brand-mark" aria-hidden="true">
            安
          </span>
          <span>
            <strong>安心到家服务</strong>
            <small>AI SERVICE DESK</small>
          </span>
        </a>
        <nav aria-label="客户服务导航">
          <a href="#services">服务范围</a>
          <a href="#promise">服务保障</a>
          <a href="tel:4008206636">联系客服</a>
        </nav>
      </header>

      <section className={`chat-stage ${hasConversation ? "chat-stage--active" : ""}`}>
        <div className="chat-intro">
          <p className="chat-eyebrow">HOME SERVICE / 01</p>
          <h1>
            {typedWelcome}
            <span aria-hidden="true" className="type-caret" />
          </h1>
          <p className="chat-intro__detail">{welcomeDetail}</p>
        </div>

        <div className="chat-surface">
          {hasConversation ? (
            <ChatMessageList isSending={isSending} messages={messages} />
          ) : (
            <div className="chat-surface__empty">
              <p>告诉我您的需求，我会先帮您确认服务范围和参考价格。</p>
            </div>
          )}

          {handoffRequired ? (
            <div className="handoff-notice" role="status">
              <strong>已为您转接人工客服</strong>
              <span>这类情况需要人工进一步确认，我们会尽快跟进处理。</span>
            </div>
          ) : null}

          {error ? (
            <div className="chat-error" role="alert">
              {error}
            </div>
          ) : null}

          <QuickPrompts disabled={isSending} onSelect={sendMessage} />
          <ChatComposer disabled={isSending} onSend={sendMessage} />
          <p className="chat-disclaimer">AI 提供参考信息，最终价格和上门时间需人工确认。</p>
        </div>
      </section>

      <footer className="customer-footer">
        <span>上海本地服务</span>
        <span>周一至周日可预约</span>
        <span>400-820-6636</span>
      </footer>
    </main>
  );
}
