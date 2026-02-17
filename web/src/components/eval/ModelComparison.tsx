interface ModelOutput {
  model: string;
  output: string;
  latencyMs: number;
  cost: number;
}

interface Props {
  outputs: ModelOutput[];
}

export default function ModelComparison({ outputs }: Props) {
  if (!outputs.length) {
    return <p className="text-sm text-gray-500">No model outputs to compare.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {outputs.map((o) => (
        <div key={o.model} className="rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <h4 className="font-mono text-sm font-medium">{o.model}</h4>
            <div className="text-xs text-gray-500">
              {o.latencyMs}ms | ${o.cost.toFixed(4)}
            </div>
          </div>
          <pre className="mt-2 max-h-60 overflow-auto text-xs whitespace-pre-wrap">
            {o.output}
          </pre>
        </div>
      ))}
    </div>
  );
}
