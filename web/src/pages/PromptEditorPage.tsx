import { useState, useCallback, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { usePromptDetail, useUpdatePrompt, usePromptHistory, usePromptContentAtSha } from "../hooks/usePrompts";
import { useAutoSave } from "../hooks/useAutoSave";
import { exportPrompty } from "../api/prompts";
import MarkdownEditor from "../components/editor/MarkdownEditor";
import FrontMatterForm from "../components/editor/FrontMatterForm";
import DiffViewer from "../components/editor/DiffViewer";
import yaml from "js-yaml";

const PROMOTION_MAP: Record<string, string> = {
  development: "staging",
  staging: "production",
};

export default function PromptEditorPage() {
  const { id } = useParams<{ id: string }>();
  const { data: prompt, isLoading } = usePromptDetail(id ?? null);
  const { data: history } = usePromptHistory(id ?? null);
  const updateMutation = useUpdatePrompt();

  const [body, setBody] = useState<string | null>(null);
  const [frontMatter, setFrontMatter] = useState<Record<string, unknown> | null>(null);
  const [commitMessage, setCommitMessage] = useState("");
  const [showRawYaml, setShowRawYaml] = useState(false);
  const [rawYaml, setRawYaml] = useState("");
  const [showDiff, setShowDiff] = useState(false);
  const [diffTargetSha, setDiffTargetSha] = useState<string | null>(null);
  const commitInputRef = useRef<HTMLInputElement>(null);

  // Initialize editor state from fetched prompt
  const currentBody = body ?? prompt?.body ?? "";
  const currentFM = frontMatter ?? (prompt ? extractFrontMatter(prompt) : {});
  const currentEnv = (currentFM.environment as string) ?? prompt?.environment ?? "development";

  // Fetch content at target SHA for diff viewer
  const { data: shaContent } = usePromptContentAtSha(
    showDiff ? (id ?? null) : null,
    diffTargetSha
  );

  useAutoSave(id ?? "new", { body: currentBody, frontMatter: currentFM });

  const handleSave = useCallback(() => {
    if (!id || !commitMessage.trim()) return;
    updateMutation.mutate({
      id,
      data: {
        front_matter: currentFM,
        body: currentBody,
        commit_message: commitMessage,
        expected_sha: prompt?.git_sha,
      },
    });
    setCommitMessage("");
  }, [id, currentFM, currentBody, commitMessage, prompt?.git_sha, updateMutation]);

  // Keyboard shortcut: Cmd+S / Ctrl+S to focus commit message
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        if (commitMessage.trim()) {
          handleSave();
        } else {
          commitInputRef.current?.focus();
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleSave, commitMessage]);

  // Sync raw YAML with front-matter state
  useEffect(() => {
    if (showRawYaml) {
      try {
        setRawYaml(yaml.dump(currentFM, { lineWidth: -1, noRefs: true }));
      } catch {
        setRawYaml("# Error serializing YAML");
      }
    }
  }, [showRawYaml, currentFM]);

  const handleRawYamlChange = useCallback(
    (value: string) => {
      setRawYaml(value);
      try {
        const parsed = yaml.load(value) as Record<string, unknown>;
        if (parsed && typeof parsed === "object") {
          setFrontMatter(parsed);
        }
      } catch {
        // Don't update FM on invalid YAML — let user keep editing
      }
    },
    [],
  );

  const handlePromote = useCallback(() => {
    const nextEnv = PROMOTION_MAP[currentEnv];
    if (!nextEnv || !id) return;
    const newFM = { ...currentFM, environment: nextEnv };
    setFrontMatter(newFM);
    updateMutation.mutate({
      id,
      data: {
        front_matter: newFM,
        body: currentBody,
        commit_message: `Promote ${prompt?.name ?? id} to ${nextEnv}`,
        expected_sha: prompt?.git_sha,
      },
    });
  }, [currentEnv, currentFM, currentBody, id, prompt, updateMutation]);

  const handleExportPrompty = useCallback(async () => {
    if (!id) return;
    try {
      const content = await exportPrompty(id);
      const blob = new Blob([content], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${prompt?.name ?? "prompt"}.prompty`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Export failed silently
    }
  }, [id, prompt?.name]);

  if (isLoading) {
    return <div className="text-sm text-gray-500">Loading prompt...</div>;
  }

  if (!prompt) {
    return <div className="text-sm text-red-500">Prompt not found</div>;
  }

  const diffBefore = shaContent?.body ?? prompt.body;

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
              currentEnv === "production"
                ? "bg-green-100 text-green-700"
                : currentEnv === "staging"
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-gray-100 text-gray-700"
            }`}
          >
            {currentEnv}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Promote button */}
          {PROMOTION_MAP[currentEnv] && (
            <button
              onClick={handlePromote}
              disabled={updateMutation.isPending}
              className="rounded border border-green-400 bg-green-50 px-3 py-1.5 text-sm text-green-700 hover:bg-green-100 disabled:opacity-50"
            >
              Promote to {PROMOTION_MAP[currentEnv]}
            </button>
          )}
          {/* Diff toggle */}
          <button
            onClick={() => {
              setShowDiff(!showDiff);
              if (!showDiff && history?.items?.[0]) {
                setDiffTargetSha(history.items[0].sha);
              }
            }}
            className={`rounded border px-3 py-1.5 text-sm ${
              showDiff
                ? "border-orange-400 bg-orange-50 text-orange-700"
                : "border-gray-300 text-gray-700 hover:bg-gray-50"
            }`}
          >
            Diff
          </button>
          <button
            onClick={() => setShowRawYaml(!showRawYaml)}
            className={`rounded border px-3 py-1.5 text-sm ${
              showRawYaml
                ? "border-blue-400 bg-blue-50 text-blue-700"
                : "border-gray-300 text-gray-700 hover:bg-gray-50"
            }`}
          >
            {showRawYaml ? "Form" : "YAML"}
          </button>
          <Link
            to={`/prompts/${id}/preview`}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
          >
            Preview
          </Link>
          {currentFM.type === "tts" && (
            <Link
              to={`/prompts/${id}/preview`}
              className="rounded border border-purple-400 bg-purple-50 px-3 py-1.5 text-sm text-purple-700 hover:bg-purple-100"
            >
              TTS Preview
            </Link>
          )}
          <Link
            to={`/prompts/${id}/eval`}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
          >
            Eval
          </Link>
          <button
            onClick={handleExportPrompty}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
          >
            Export .prompty
          </button>
          <span className="text-xs text-gray-400" title="Cmd+S to save">
            {navigator.platform.includes("Mac") ? "\u2318" : "Ctrl"}+S
          </span>
        </div>
      </div>

      {/* Diff SHA selector */}
      {showDiff && history?.items && (
        <div className="mt-2 flex items-center gap-2 text-sm">
          <span className="text-gray-500">Compare with:</span>
          <select
            value={diffTargetSha ?? ""}
            onChange={(e) => setDiffTargetSha(e.target.value || null)}
            className="rounded border border-gray-300 px-2 py-1 text-xs"
          >
            {history.items.map((c: { sha: string; message: string }) => (
              <option key={c.sha} value={c.sha}>
                {c.sha.slice(0, 7)} — {c.message.split("\n")[0].slice(0, 40)}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Split pane */}
      <div className="mt-4 flex flex-1 gap-4 overflow-hidden">
        {/* Left: Front-matter form or raw YAML */}
        <div className="w-80 flex-shrink-0 overflow-auto rounded-lg border border-gray-200 bg-white p-4">
          {showRawYaml ? (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-gray-900">Raw YAML</h3>
              <textarea
                value={rawYaml}
                onChange={(e) => handleRawYamlChange(e.target.value)}
                className="h-full min-h-[400px] w-full rounded border border-gray-300 p-2 font-mono text-xs"
                spellCheck={false}
              />
            </div>
          ) : (
            <FrontMatterForm
              value={currentFM}
              onChange={(fm) => setFrontMatter(fm)}
            />
          )}
        </div>

        {/* Right: Editor or Diff viewer */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden rounded-lg border border-gray-200">
            {showDiff ? (
              <div className="h-full overflow-auto p-4">
                <DiffViewer
                  before={diffBefore}
                  after={currentBody}
                  labelBefore={diffTargetSha ? `${diffTargetSha.slice(0, 7)}` : "Last commit"}
                  labelAfter="Current"
                />
              </div>
            ) : (
              <MarkdownEditor value={currentBody} onChange={setBody} />
            )}
          </div>

          {/* Commit bar */}
          <div className="mt-3 flex items-center gap-2">
            <input
              ref={commitInputRef}
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
          {history.items.slice(0, 5).map((commit: { sha: string; message: string }) => (
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
