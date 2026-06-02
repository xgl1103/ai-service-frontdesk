type QuickPromptsProps = {
  disabled?: boolean;
  onSelect: (prompt: string) => void | Promise<void>;
};

const prompts = [
  "深度保洁多少钱？",
  "你们服务哪些区域？",
  "维修后保修多久？",
  "帮我预约水管维修",
];

export function QuickPrompts({ disabled = false, onSelect }: QuickPromptsProps) {
  return (
    <div aria-label="快捷问题" className="quick-prompts">
      {prompts.map((prompt) => (
        <button disabled={disabled} key={prompt} onClick={() => void onSelect(prompt)} type="button">
          {prompt}
        </button>
      ))}
    </div>
  );
}

