import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BugCast — every user bug report becomes a runnable test",
  description:
    "Upload a screen recording. Get a Playwright script that reproduces the bug. Powered by a 72B VLM on AMD MI300X.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-neutral-950 text-neutral-100 antialiased">{children}</body>
    </html>
  );
}
