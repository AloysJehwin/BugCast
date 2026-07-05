"use client";

import { useState } from "react";
import { Uploader } from "@/components/Uploader";
import { PipelineProgress } from "@/components/PipelineProgress";
import { CostCounter } from "@/components/CostCounter";
import { ScriptView } from "@/components/ScriptView";

export default function Home() {
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  async function onUpload(file: File) {
    setLoading(true);
    const fd = new FormData();
    fd.append("video", file);
    try {
      const r = await fetch("/api/analyze", { method: "POST", body: fd });
      setResult(await r.json());
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-10">
        <h1 className="text-4xl font-semibold tracking-tight">BugCast</h1>
        <p className="mt-2 text-neutral-400">
          Every user bug report becomes a runnable test. Powered by a 72B VLM on AMD MI300X.
        </p>
      </header>

      <Uploader onUpload={onUpload} disabled={loading} />
      <PipelineProgress loading={loading} result={result} />
      {result && (
        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ScriptView script={result.script} />
          <CostCounter result={result} />
        </div>
      )}
    </main>
  );
}
