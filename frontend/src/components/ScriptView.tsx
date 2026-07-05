"use client";

export function ScriptView({ script }: { script: string }) {
  function download() {
    const blob = new Blob([script], { type: "text/typescript" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "bugcast.spec.ts";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-6">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm uppercase tracking-wider text-neutral-400">Repro script</h3>
        <button
          onClick={download}
          className="rounded-lg bg-neutral-800 px-3 py-1 text-xs hover:bg-neutral-700"
        >
          Download .spec.ts
        </button>
      </div>
      <pre className="max-h-80 overflow-auto rounded-lg bg-black/60 p-4 text-xs text-neutral-200">
        <code>{script}</code>
      </pre>
    </div>
  );
}
