"use client";

import { useRef } from "react";

export function Uploader({
  onUpload,
  disabled,
}: {
  onUpload: (f: File) => void;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <div
      className="flex h-56 cursor-pointer items-center justify-center rounded-2xl border-2 border-dashed border-neutral-700 bg-neutral-900 transition hover:border-neutral-500"
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        const f = e.dataTransfer.files?.[0];
        if (f) onUpload(f);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
        disabled={disabled}
      />
      <p className="text-neutral-400">
        {disabled ? "Analyzing…" : "Drop a screen recording, or click to choose"}
      </p>
    </div>
  );
}
