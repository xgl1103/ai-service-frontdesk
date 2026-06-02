import { useEffect, useRef } from "react";

export type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
};

type ChatMessageListProps = {
  messages: ChatMessage[];
  isSending?: boolean;
};

export function ChatMessageList({ messages, isSending = false }: ChatMessageListProps) {
  const listEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [isSending, messages]);

  return (
    <div aria-live="polite" className="chat-message-list" role="log">
      {messages.map((message) => (
        <article className={`chat-message chat-message--${message.role}`} key={message.id}>
          <span className="chat-message__label">
            {message.role === "assistant" ? "安心到家" : "您"}
          </span>
          <p>{message.content}</p>
        </article>
      ))}

      {isSending ? (
        <article className="chat-message chat-message--assistant chat-message--loading">
          <span className="chat-message__label">安心到家</span>
          <p>
            <span />
            <span />
            <span />
          </p>
        </article>
      ) : null}
      <div ref={listEndRef} />
    </div>
  );
}

