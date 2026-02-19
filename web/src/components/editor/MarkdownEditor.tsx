import CodeMirror from "@uiw/react-codemirror";
import { markdown } from "@codemirror/lang-markdown";
import { oneDark } from "@codemirror/theme-one-dark";
import { StreamLanguage } from "@codemirror/language";
import { LanguageSupport } from "@codemirror/language";

/**
 * Simple Jinja2 token highlighting using StreamLanguage.
 * Highlights {{ variables }}, {% tags %}, and {# comments #}.
 */
const jinja2StreamParser = {
  startState() {
    return { inBlock: null as string | null };
  },
  token(stream: { match: (re: RegExp) => string[] | null; next: () => string; eol: () => boolean }, state: { inBlock: string | null }) {
    // Inside a Jinja2 block
    if (state.inBlock === "variable") {
      if (stream.match(/\}\}/)) { state.inBlock = null; return "atom"; }
      stream.next();
      return "atom";
    }
    if (state.inBlock === "tag") {
      if (stream.match(/%\}/)) { state.inBlock = null; return "keyword"; }
      stream.next();
      return "keyword";
    }
    if (state.inBlock === "comment") {
      if (stream.match(/#\}/)) { state.inBlock = null; return "comment"; }
      stream.next();
      return "comment";
    }

    // Look for Jinja2 block openings
    if (stream.match(/\{\{/)) { state.inBlock = "variable"; return "atom"; }
    if (stream.match(/\{%/)) { state.inBlock = "tag"; return "keyword"; }
    if (stream.match(/\{#/)) { state.inBlock = "comment"; return "comment"; }

    // Default markdown text
    stream.next();
    return null;
  },
};

const jinja2Language = new LanguageSupport(StreamLanguage.define(jinja2StreamParser));

interface Props {
  value: string;
  onChange: (value: string) => void;
}

export default function MarkdownEditor({ value, onChange }: Props) {
  return (
    <CodeMirror
      value={value}
      onChange={onChange}
      extensions={[markdown(), jinja2Language]}
      theme={oneDark}
      className="h-full"
      basicSetup={{
        lineNumbers: true,
        foldGutter: true,
        highlightActiveLine: true,
      }}
    />
  );
}
