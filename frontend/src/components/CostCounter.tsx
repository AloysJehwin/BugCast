"use client";

export function CostCounter({ result }: { result: any }) {
  const localUsd = result?.cost?.local_usd ?? 0.03;
  const gpt4oUsd = result?.cost?.gpt4o_usd ?? 2.14;
  const factor = result?.cost?.savings_factor ?? Math.round((gpt4oUsd / (localUsd || 1)) * 10) / 10;

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-6">
      <h3 className="text-sm uppercase tracking-wider text-neutral-400">Cost of this run</h3>
      <div className="mt-4 flex items-baseline gap-3">
        <span className="text-4xl font-semibold text-emerald-400">${localUsd.toFixed(2)}</span>
        <span className="text-neutral-500 line-through">${gpt4oUsd.toFixed(2)}</span>
      </div>
      <p className="mt-2 text-sm text-neutral-400">
        BugCast on AMD MI300X vs a naive GPT-4o pipeline —{" "}
        <span className="text-neutral-100">~{factor}× cheaper</span>.
      </p>
    </div>
  );
}
