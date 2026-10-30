"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

// Rendered outside the intl provider when a segment crashes, so copy is bilingual and static.
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto flex min-h-[75vh] max-w-md flex-col items-center justify-center gap-5 px-6 text-center">
      <span className="font-serif text-3xl font-medium tracking-wide text-brand">karu</span>
      <div>
        <h1 className="font-serif text-h2 text-ink-900">
          Something went wrong · कुछ गड़बड़ हो गई
        </h1>
        <p className="text-body-s text-muted mt-2 leading-relaxed">
          Please try again. If you were creating a listing or saving draft details, it is securely cached on this device.
        </p>
      </div>

      <div className="flex gap-3">
        <Button variant="primary" size="M" onClick={reset}>
          Try again · फिर से कोशिश करें
        </Button>
        <Link href="/">
          <Button variant="ghost" size="M">
            Home
          </Button>
        </Link>
      </div>

      {error.digest && (
        <p className="text-caption font-mono text-subtle">
          Reference code: {error.digest}
        </p>
      )}
    </main>
  );
}
