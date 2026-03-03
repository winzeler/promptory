import { useState } from "react";
import Modal from "../layout/Modal";
import { useCreatePrompt } from "../../hooks/usePrompts";

interface Props {
  appId: string;
  onClose: () => void;
  onCreated: (promptId: string) => void;
}

export default function CreatePromptModal({ appId, onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState("chat");
  const [role, setRole] = useState("system");
  const [environment, setEnvironment] = useState("development");
  const [commitMessage, setCommitMessage] = useState("");
  const [error, setError] = useState("");

  const { mutateAsync, isPending } = useCreatePrompt();

  const effectiveCommitMessage = commitMessage || (name ? `Add ${name}` : "");

  const handleNameChange = (val: string) => {
    setName(val);
    if (!commitMessage) {
      // leave controlled by effectiveCommitMessage
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const result = await mutateAsync({
        app_id: appId,
        name,
        ...(domain && { domain }),
        ...(description && { description }),
        type,
        role,
        environment,
        commit_message: effectiveCommitMessage,
      });
      const id = (result as { id: string }).id;
      onCreated(id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create prompt";
      setError(msg);
    }
  };

  return (
    <Modal title="New Prompt" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">
            Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder="my_prompt_name"
            className="w-full rounded border border-gray-300 px-3 py-1.5 font-mono text-sm focus:border-blue-500 focus:outline-none"
            autoFocus
          />
          <p className="mt-0.5 text-xs text-gray-400">Use snake_case</p>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">Domain</label>
          <input
            type="text"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="e.g. meditation"
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="chat">chat</option>
              <option value="completion">completion</option>
              <option value="tts">tts</option>
              <option value="transcription">transcription</option>
              <option value="image">image</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="system">system</option>
              <option value="user">user</option>
              <option value="assistant">assistant</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Environment</label>
            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="development">development</option>
              <option value="staging">staging</option>
              <option value="production">production</option>
            </select>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">Commit message</label>
          <input
            type="text"
            value={commitMessage}
            onChange={(e) => setCommitMessage(e.target.value)}
            placeholder={name ? `Add ${name}` : "Add prompt"}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        {error && (
          <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-gray-300 px-4 py-1.5 text-sm hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isPending || !name.trim()}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isPending ? "Creating..." : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
