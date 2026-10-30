"use client";

import { CloudOff } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Suspense, useEffect, useState } from "react";
import { PhotoStep, VoiceStep, type PhotoItem } from "@/components/artisan/capture";
import { FinalStep, Published } from "@/components/artisan/publish";
import { Processing, ReviewStep, useListing } from "@/components/artisan/review";
import { SellPage } from "@/components/artisan/shell";
import { AuthGate } from "@/components/auth-gate";
import { Banner, Button, Skeleton } from "@/components/ui";
import { usePublicConfig } from "@/lib/hooks";
import { db, enqueueDraft, onOutboxChange, processOutbox } from "@/lib/offline";
import type { Recording } from "@/lib/speech";

type Step = "photos" | "voice" | "uploading" | "processing" | "review" | "final" | "published";

/** F2 Snap + Speak — target: first listing in under 5 minutes. */
export default function NewListingPage() {
  return (
    <Suspense>
      <AuthGate require="artisan">{() => <SnapSpeak />}</AuthGate>
    </Suspense>
  );
}

function SnapSpeak() {
  const t = useTranslations("sell.new");
  const locale = useLocale();
  const router = useRouter();
  const params = useSearchParams();
  const { data: config } = usePublicConfig();
  const [step, setStep] = useState<Step>(params.get("listing") ? "processing" : "photos");
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [outboxId, setOutboxId] = useState<number | null>(null);
  const [listingId, setListingId] = useState<string | null>(params.get("listing"));
  const [jobId, setJobId] = useState<string | null>(null);
  const [published, setPublished] = useState<{ karu_ids: string[]; short_code: string; verification_status: string } | null>(null);
  const listing = useListing(listingId);

  // Resume an existing draft: follow its processing job, or go straight to review when it's done.
  const resumeJob = !jobId && step === "processing" ? listing.data?.processing : undefined;
  const resumeDone = !!listing.data && !jobId && step === "processing" && (!resumeJob || resumeJob.status === "completed" || resumeJob.status === "failed");
  const activeJob = jobId || (resumeJob && !resumeDone ? resumeJob.job_id : null);
  const currentStep: Step = resumeDone ? "review" : step;

  // Follow the outbox item until the server has created the draft.
  useEffect(() => {
    if (outboxId === null) return;
    const check = async () => {
      const item = await db().outbox.get(outboxId);
      if (item?.listingId && item.jobId) {
        setListingId(item.listingId);
        setJobId(item.jobId);
        setStep("processing");
      }
    };
    void check();
    return onOutboxChange(() => void check());
  }, [outboxId]);

  const submit = async (rec: Recording | null) => {
    const id = await enqueueDraft({
      photos: photos.map((p) => p.file),
      voice: rec?.blob ?? null,
      voiceDuration: rec?.durationS ?? null,
      transcript: rec?.transcript || "",
      sourceLang: locale,
    });
    setOutboxId(id);
    setStep("uploading");
    void processOutbox();
  };

  return (
    <SellPage>
      {currentStep === "photos" && <PhotoStep photos={photos} setPhotos={setPhotos} max={config?.limits.photos_max ?? 6} onNext={() => setStep("voice")} />}
      {currentStep === "voice" && <VoiceStep maxSeconds={config?.limits.voice_note_max_s ?? 120} onDone={(r) => void submit(r)} onSkip={() => void submit(null)} />}
      {currentStep === "uploading" && <Uploading onHome={() => router.push("/sell")} />}
      {currentStep === "processing" && activeJob && <Processing jobId={activeJob} onDone={async () => { await listing.refetch(); setStep("review"); }} />}
      {currentStep === "processing" && !activeJob && <Skeleton className="h-64" />}
      {currentStep === "review" && (listing.data ? <ReviewStep key={`${listing.data.id}-${JSON.stringify(listing.data.attributes)}-${listing.data.category_slug}`} listing={listing.data} onNext={() => setStep("final")} /> : <Skeleton className="h-96" />)}
      {currentStep === "final" && listing.data && <FinalStep listing={listing.data} onPublished={(r) => { setPublished(r); setStep("published"); }} />}
      {currentStep === "published" && listing.data && published && <Published listing={listing.data} result={published} />}
      {currentStep === "review" && listing.data && listing.data.status !== "draft" && listing.data.status !== "processing" && (
        <Banner tone="info" action={<Link href={`/sell/products/${listing.data.id}`} className="font-semibold underline">{t("open")}</Link>}>{t("already_published")}</Banner>
      )}
    </SellPage>
  );
}

function Uploading({ onHome }: { onHome: () => void }) {
  const t = useTranslations("sell.new");
  const [online, setOnline] = useState(true);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  return (
    <section className="flex flex-col items-center gap-5 py-10 text-center">
      {online ? (
        <>
          <div className="size-16 animate-spin rounded-full border-4 border-brand-soft border-t-brand" />
          <h1 className="font-display text-2xl">{t("sending")}</h1>
          <p className="text-ink-600">{t("sending_body")}</p>
        </>
      ) : (
        <>
          <CloudOff className="size-14 text-gold-500" />
          <h1 className="font-display text-2xl">{t("waiting_network")}</h1>
          <p className="text-ink-600">{t("saved_on_phone")}</p>
          <Button variant="secondary" onClick={onHome}>{t("go_home")}</Button>
        </>
      )}
    </section>
  );
}
