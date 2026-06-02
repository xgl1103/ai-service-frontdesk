import { useState } from "react";
import type { FormEvent } from "react";

type ChatComposerProps = {
  disabled?: boolean;
  onSend: (message: string) => void | Promise<void>;
};

export function ChatComposer({ disabled = false, onSend }: ChatComposerProps) {
  const [message, setMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanMessage = message.trim();

    if (!cleanMessage || disabled) {
      return;
    }

    setMessage("");
    await onSend(cleanMessage);
  }

  return (
    <form className="chat-composer" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor="customer-message">
        输入您的问题
      </label>
      <input
        id="customer-message"
        autoComplete="off"
        disabled={disabled}
        maxLength={500}
        onChange={(event) => setMessage(event.target.value)}
        placeholder={disabled ? "正在为您查询..." : "描述您的需求，例如：厨房水管漏水"}
        type="text"
        value={message}
      />
      <button disabled={disabled || !message.trim()} type="submit">
        <span>{disabled ? "发送中" : "发送"}</span>
        <span aria-hidden="true" className="send-arrow">
          →
        </span>
      </button>
    </form>
  );
}
