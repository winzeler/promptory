interface Props {
  before: string;
  after: string;
}

export default function DiffViewer({ before, after }: Props) {
  // Phase 4: Side-by-side diff visualization
  return (
    <div className="grid grid-cols-2 gap-2 text-xs font-mono">
      <div className="rounded border border-red-200 bg-red-50 p-3 whitespace-pre-wrap">
        {before || "(empty)"}
      </div>
      <div className="rounded border border-green-200 bg-green-50 p-3 whitespace-pre-wrap">
        {after || "(empty)"}
      </div>
    </div>
  );
}
