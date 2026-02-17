import { EvalRun } from "../../api/eval";

interface Props {
  runs: EvalRun[];
}

export default function EvalResults({ runs }: Props) {
  if (!runs.length) {
    return <p className="text-sm text-gray-500">No evaluation runs.</p>;
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
          <th className="py-2">Model</th>
          <th className="py-2">Status</th>
          <th className="py-2">Cost</th>
          <th className="py-2">Duration</th>
          <th className="py-2">Date</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr key={run.id} className="border-b border-gray-100">
            <td className="py-2 font-mono">{run.model}</td>
            <td className="py-2">
              <span className={`rounded px-1.5 py-0.5 text-xs ${
                run.status === "completed" ? "bg-green-100 text-green-700" :
                run.status === "failed" ? "bg-red-100 text-red-700" :
                "bg-gray-100 text-gray-700"
              }`}>
                {run.status}
              </span>
            </td>
            <td className="py-2 text-gray-500">
              {run.cost_usd != null ? `$${run.cost_usd.toFixed(4)}` : "--"}
            </td>
            <td className="py-2 text-gray-500">
              {run.duration_ms != null ? `${run.duration_ms}ms` : "--"}
            </td>
            <td className="py-2 text-gray-500">
              {new Date(run.created_at).toLocaleString()}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
