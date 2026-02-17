import { useState } from "react";

interface Props {
  onCommit: (message: string) => void;
  isPending: boolean;
}

export default function CommitDialog({ onCommit, isPending }: Props) {
  const [message, setMessage] = useState("");

  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        placeholder="Commit message..."
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && message.trim()) {
            onCommit(message);
            setMessage("");
          }
        }}
        className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
      />
      <button
        onClick={() => {
          if (message.trim()) {
            onCommit(message);
            setMessage("");
          }
        }}
        disabled={!message.trim() || isPending}
        className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
      >
        {isPending ? "Committing..." : "Commit"}
      </button>
    </div>
  );
}
