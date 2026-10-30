import Link from "next/link";
import { ArrowRight, Info, Play, ShieldCheck } from "lucide-react";
import { KaruIdChip, ProofChecks, Woven } from "./badges";
import { cx } from "@/lib/format";
import type { ProofCheck, VerificationStatus } from "@/lib/types";

export interface ProvenancePanelProps {
  code: string;
  verification: VerificationStatus;
  checks: ProofCheck[];
  photosOriginal?: boolean | null;
  registry?: { kind: string; date: string }[];
  makingVideo?: { url: string; poster: string | null } | null;
  className?: string;
}

export function ProvenancePanel({
  code,
  verification,
  checks,
  photosOriginal,
  registry,
  makingVideo,
  className,
}: ProvenancePanelProps) {
  const isVerified = verification === "verified";

  return (
    <div
      className={cx(
        "rounded-sm border p-6 flex flex-col gap-5 transition-colors",
        isVerified ? "border-peacock-200 bg-verified-soft" : "border-line bg-surface",
        className
      )}
    >
      <Woven />

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className={cx("size-5", isVerified ? "text-peacock-700" : "text-muted")} />
          <h3 className="font-serif text-h3 text-text">Proof of Handmade</h3>
        </div>
        <KaruIdChip code={code} />
      </div>

      <ProofChecks checks={checks} photosOriginal={photosOriginal} registry={registry} />

      {makingVideo && (
        <div className="rounded-xs border border-line bg-surface p-3.5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-full bg-peacock-100 text-peacock-800">
              <Play className="size-4 fill-current" />
            </span>
            <div className="flex flex-col">
              <span className="text-body-s font-semibold text-text">Artisan Making Proof Video</span>
              <span className="text-caption text-muted">Filmed by artisan during batch creation</span>
            </div>
          </div>
          <Link
            href={`/k/${code}`}
            className="text-caption font-semibold text-brand hover:underline shrink-0"
          >
            Watch Proof →
          </Link>
        </div>
      )}

      <div className="flex items-center justify-between border-t border-line pt-3 text-caption">
        <Link
          href="/verification-explained"
          className="inline-flex items-center gap-1 text-muted hover:text-brand transition-colors"
        >
          <Info className="size-3.5" /> What does verified mean?
        </Link>
        <Link
          href={`/k/${code}`}
          className="inline-flex items-center gap-1 font-semibold text-brand hover:underline"
        >
          <span>View Public Certificate</span>
          <ArrowRight className="size-3.5 flip-rtl" />
        </Link>
      </div>
    </div>
  );
}
