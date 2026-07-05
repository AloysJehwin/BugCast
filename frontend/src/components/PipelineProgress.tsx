"use client";

const STAGES = [
  "Extracting frames",
  "Filtering scene changes",
  "OCR + UI detection",
  "Inferring events",
  "VLM reasoning on MI300X",
  "Generating script",
  "Replaying + diffing",
];

export function PipelineProgress({ loading, result }: { loading: boolean; result: any | null }) {
  const done = result != null;
  return (
    <ol className="mt-8 space-y-2 text-sm">
      {STAGES.map((label, i) => (
        <li key={label} className="flex items-center gap-3">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              done ? "bg-emerald-400" : loading ? "bg-amber-400 animate-pulse" : "bg-neutral-700"
            }`}
          />
          <span className={done ? "text-neutral-200" : "text-neutral-400"}>{label}</span>
        </li>
      ))}
    </ol>
  );
}
