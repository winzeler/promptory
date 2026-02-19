import { useMemo } from "react";

interface Props {
  before: string;
  after: string;
  labelBefore?: string;
  labelAfter?: string;
}

type LineType = "same" | "added" | "removed";

interface DiffLine {
  type: LineType;
  lineA?: string;
  lineB?: string;
  numA?: number;
  numB?: number;
}

function computeDiff(a: string, b: string): DiffLine[] {
  const linesA = a.split("\n");
  const linesB = b.split("\n");

  // Simple LCS-based diff
  const m = linesA.length;
  const n = linesB.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] = linesA[i - 1] === linesB[j - 1] ? dp[i - 1][j - 1] + 1 : Math.max(dp[i - 1][j], dp[i][j - 1]);
    }
  }

  // Backtrack to build diff
  const result: DiffLine[] = [];
  let i = m,
    j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && linesA[i - 1] === linesB[j - 1]) {
      result.push({ type: "same", lineA: linesA[i - 1], lineB: linesB[j - 1], numA: i, numB: j });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.push({ type: "added", lineB: linesB[j - 1], numB: j });
      j--;
    } else {
      result.push({ type: "removed", lineA: linesA[i - 1], numA: i });
      i--;
    }
  }

  return result.reverse();
}

export default function DiffViewer({ before, after, labelBefore = "Before", labelAfter = "After" }: Props) {
  const diff = useMemo(() => computeDiff(before, after), [before, after]);

  if (before === after) {
    return <p className="text-xs text-gray-500">No differences.</p>;
  }

  const stats = diff.reduce(
    (acc, d) => {
      if (d.type === "added") acc.added++;
      if (d.type === "removed") acc.removed++;
      return acc;
    },
    { added: 0, removed: 0 },
  );

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span className="text-green-600">+{stats.added}</span>
        <span className="text-red-600">-{stats.removed}</span>
      </div>
      <div className="overflow-auto rounded border border-gray-200 text-xs font-mono">
        {/* Headers */}
        <div className="grid grid-cols-2 border-b border-gray-200 bg-gray-50">
          <div className="border-r border-gray-200 px-3 py-1.5 font-sans text-xs font-semibold text-gray-600">
            {labelBefore}
          </div>
          <div className="px-3 py-1.5 font-sans text-xs font-semibold text-gray-600">{labelAfter}</div>
        </div>
        {/* Lines */}
        {diff.map((d, idx) => (
          <div key={idx} className="grid grid-cols-2">
            {d.type === "same" ? (
              <>
                <div className="border-r border-gray-100 px-3 py-0.5 whitespace-pre-wrap text-gray-700">
                  <span className="mr-2 inline-block w-6 text-right text-gray-300">{d.numA}</span>
                  {d.lineA}
                </div>
                <div className="px-3 py-0.5 whitespace-pre-wrap text-gray-700">
                  <span className="mr-2 inline-block w-6 text-right text-gray-300">{d.numB}</span>
                  {d.lineB}
                </div>
              </>
            ) : d.type === "removed" ? (
              <>
                <div className="border-r border-gray-100 bg-red-50 px-3 py-0.5 whitespace-pre-wrap text-red-800">
                  <span className="mr-2 inline-block w-6 text-right text-red-300">{d.numA}</span>
                  {d.lineA}
                </div>
                <div className="bg-red-50/30 px-3 py-0.5" />
              </>
            ) : (
              <>
                <div className="border-r border-gray-100 bg-green-50/30 px-3 py-0.5" />
                <div className="bg-green-50 px-3 py-0.5 whitespace-pre-wrap text-green-800">
                  <span className="mr-2 inline-block w-6 text-right text-green-300">{d.numB}</span>
                  {d.lineB}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
