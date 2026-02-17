import { useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { usePromptDetail, useUpdatePrompt, usePromptHistory } from "../hooks/usePrompts";
import { useAutoSave } from "../hooks/useAutoSave";
import MarkdownEditor from "../components/editor/MarkdownEditor";
import FrontMatterForm from "../components/editor/FrontMatterForm";

export default function PromptEditorPage() {
  const { id } = useParams<{ id: string }>();
  const { data: prompt, isLoading } = usePromptDetail(id ?? null);
  const { data: history } = usePromptHistory(id ?? null);
  const updateMutation = useUpdatePrompt();

  const [body, setBody] = useState<string | null>(null);
  const [frontMatter, setFrontMatter] = useState<Record<string, unknown> | null>(null);
  const [commitMessage, setCommitMessage] = useState("");

  // Initialize editor state from fetched prompt
  const currentBody = body ?? prompt?.body ?? "";
  const currentFM = frontMatter ?? (prompt ? extractFrontMatter(prompt) : {});

  useAutoSave(id ?? "new", { body: currentBody, frontMatter: currentFM });

  const handleSave = useCallback(() => {
    if (!id || !commitMessage.trim()) return;
    updateMutation.mutate({
      id,
      data: {
        front_matter: currentFM,
        body: currentBody,
        commit_message: commitMessage,
      },
    });
    setCommitMessage("");
  }, [id, currentFM, currentBody, commitMessage, updateMutation]);

  if (isLoading) {
    return <div className="text-sm text-gray-500">Loading prompt...</div>;
  }

  if (!prompt) {
    return <div className="text-sm text-red-500">Prompt not found</div>;
  }

  return (
    <div className="flex h-full flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-gray-200 pb-4">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-sm text-gray-500 hover:text-gray-700">
            &larr; Back
          </Link>
          <h1 className="font-mono text-lg font-bold text-gray-900">
            {prompt.name}
          </h1>
          {prompt.version && (
            <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
              v{prompt.version}
            </span>
          )}
          <span
            className={`rounded px-2 py-0.5 text-xs font-medium ${
              prompt.environment === "production"
                ? "bg-green-100 text-green-700"
                : "bg-gray-100 text-gray-700"
            }`}
          >
            {prompt.environment}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to={`/prompts/${id}/preview`}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
          >
            Preview
          </Link>
          <Link
            to={`/prompts/${id}/eval`}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
          >
            Eval
          </Link>
        </div>
      </div>

      {/* Split pane */}
      <div className="mt-4 flex flex-1 gap-4 overflow-hidden">
        {/* Left: Front-matter form */}
        <div className="w-80 flex-shrink-0 overflow-auto rounded-lg border border-gray-200 bg-white p-4">
          <FrontMatterForm
            value={currentFM}
            onChange={(fm) => setFrontMatter(fm)}
          />
        </div>

        {/* Right: Markdown editor */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden rounded-lg border border-gray-200">
            <MarkdownEditor value={currentBody} onChange={setBody} />
          </div>

          {/* Commit bar */}
          <div className="mt-3 flex items-center gap-2">
            <input
              type="text"
              placeholder="Commit message..."
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
            />
            <button
              onClick={handleSave}
              disabled={!commitMessage.trim() || updateMutation.isPending}
              className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
            >
              {updateMutation.isPending ? "Saving..." : "Save & Commit"}
            </button>
          </div>

          {updateMutation.isError && (
            <p className="mt-1 text-xs text-red-500">
              Error: {(updateMutation.error as Error).message}
            </p>
          )}
          {updateMutation.isSuccess && (
            <p className="mt-1 text-xs text-green-600">Saved and committed!</p>
          )}
        </div>
      </div>

      {/* Git history bar */}
      {history?.items && history.items.length > 0 && (
        <div className="mt-3 flex items-center gap-4 overflow-x-auto border-t border-gray-200 pt-3 text-xs text-gray-500">
          <span className="font-medium">History:</span>
          {history.items.slice(0, 5).map((commit) => (
            <span key={commit.sha} className="whitespace-nowrap">
              <code className="text-gray-600">{commit.sha.slice(0, 7)}</code>{" "}
              {commit.message.split("\n")[0].slice(0, 40)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function extractFrontMatter(prompt: Record<string, unknown>): Record<string, unknown> {
  const { body: _body, git_sha: _sha, updated_at: _upd, ...fm } = prompt;
  return fm;
}
