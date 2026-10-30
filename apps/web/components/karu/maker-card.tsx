"use client";

import { Pause, Play, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { cx } from "@/lib/format";
import { useMe } from "@/lib/hooks";
import type { Maker } from "@/lib/types";

export function MakerAvatar({
  maker,
  size = 56,
}: {
  maker: Pick<Maker, "photo_url" | "name">;
  size?: number;
}) {
  return maker.photo_url ? (
    <img
      src={maker.photo_url}
      alt={maker.name}
      width={size}
      height={size}
      className="shrink-0 rounded-full object-cover border border-line"
      style={{ width: size, height: size }}
    />
  ) : (
    <span
      className="flex shrink-0 items-center justify-center rounded-full bg-sand-200 text-brand"
      style={{ width: size, height: size }}
    >
      <UserRound className="size-1/2" />
    </span>
  );
}

export function ListenButton({ url, name }: { url: string; name: string }) {
  const t = useTranslations("maker");
  const ref = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => {
          const a = ref.current;
          if (!a) return;
          if (a.paused) void a.play();
          else a.pause();
        }}
        className="inline-flex min-h-10 items-center gap-2 rounded-xs border border-line bg-surface px-3.5 text-caption font-semibold text-text hover:border-brand hover:text-brand cursor-pointer transition-colors"
      >
        {playing ? <Pause className="size-4 text-brand" /> : <Play className="size-4 text-brand" />}
        <span>{t("listen", { name: name.split(" ")[0] })}</span>
      </button>
      <audio
        ref={ref}
        src={url}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />
    </>
  );
}

export function FollowButton({ artisanId, initial }: { artisanId: string; initial?: boolean }) {
  const t = useTranslations("maker");
  const router = useRouter();
  const { data: me } = useMe();
  const [following, setFollowing] = useState(!!initial);
  const [busy, setBusy] = useState(false);

  return (
    <button
      type="button"
      disabled={busy}
      onClick={async () => {
        if (!me) {
          router.push(`/login?next=${encodeURIComponent(window.location.pathname)}`);
          return;
        }
        setBusy(true);
        try {
          await api(`/follows/${artisanId}`, { method: following ? "DELETE" : "POST" });
          setFollowing(!following);
        } finally {
          setBusy(false);
        }
      }}
      className={cx(
        "min-h-10 rounded-xs px-4 text-caption font-semibold transition-colors cursor-pointer",
        following
          ? "border border-line bg-brand-soft text-brand"
          : "bg-brand text-white hover:bg-brand-hover"
      )}
      aria-pressed={following}
    >
      {following ? t("following") : t("follow")}
    </button>
  );
}

/** MakerCard: compact, feature (PDP), tile (directory). */
export function MakerCard({
  maker,
  variant = "compact",
  compact,
}: {
  maker: Maker;
  variant?: "compact" | "feature" | "tile";
  compact?: boolean;
}) {
  const t = useTranslations("maker");
  const resolvedVariant = compact ? "compact" : variant;

  // Feature variant: PDP "Meet the Maker" band
  if (resolvedVariant === "feature") {
    return (
      <section className="rounded-sm border border-line bg-surface-alt p-6 sm:p-10" aria-labelledby="meet-maker-heading">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center">
          <div className="md:col-span-4 relative aspect-[4/5] overflow-hidden rounded-t-[60px] rounded-b-sm border border-line bg-sand-200">
            {maker.photo_url ? (
              <img src={maker.photo_url} alt={maker.name} className="size-full object-cover" loading="lazy" />
            ) : (
              <div className="flex size-full items-center justify-center font-serif text-4xl text-brand">{maker.name[0]}</div>
            )}
          </div>

          <div className="md:col-span-8 flex flex-col gap-4">
            <div>
              <p className="text-eyebrow text-brand mb-1">{t("meet") || "Meet the Maker"}</p>
              <h2 id="meet-maker-heading" className="font-serif text-h2 text-text font-medium">
                {maker.name}
              </h2>
              <p className="text-body-s text-muted mt-0.5">{maker.place}</p>
            </div>

            {maker.story && (
              <blockquote className="font-serif text-body sm:text-body-l italic leading-relaxed text-ink-800 border-s-2 border-brand ps-4 py-1" lang={maker.story_lang}>
                “{maker.story}”
              </blockquote>
            )}

            <div className="flex flex-wrap items-center gap-4 text-caption text-muted border-t border-line pt-3">
              <span className="font-semibold text-peacock-700">
                ✓ Karu Passport Verified
              </span>
              {maker.years_of_practice && (
                <span>· {maker.years_of_practice} Years of Generational Craft</span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <FollowButton artisanId={maker.id} initial={maker.following} />
              {maker.voice_url && <ListenButton url={maker.voice_url} name={maker.name} />}
              <Link href={`/m/${maker.handle}`} className="text-eyebrow text-brand hover:underline ms-2">
                All pieces by {maker.name.split(" ")[0]} →
              </Link>
            </div>
          </div>
        </div>
      </section>
    );
  }

  // Tile variant: makers directory / following grid
  if (resolvedVariant === "tile") {
    return (
      <Link
        href={`/m/${maker.handle}`}
        className="group flex flex-col rounded-sm border border-line bg-surface p-4 transition-all hover:border-brand hover:shadow-sm"
      >
        <div className="relative aspect-square w-full overflow-hidden rounded-xs bg-sand-200 mb-3">
          {maker.photo_url ? (
            <img src={maker.photo_url} alt={maker.name} className="size-full object-cover transition-transform group-hover:scale-105" loading="lazy" />
          ) : (
            <div className="flex size-full items-center justify-center font-serif text-3xl text-brand">{maker.name[0]}</div>
          )}
        </div>
        <h3 className="font-serif text-h4 text-text group-hover:text-brand transition-colors truncate">
          {maker.name}
        </h3>
        <p className="text-caption text-muted truncate">{maker.place}</p>
        <div className="mt-3 flex items-center justify-between border-t border-line pt-2 text-caption">
          <span className="text-peacock-700 font-medium">✓ Verified</span>
          <span className="text-muted">Explore →</span>
        </div>
      </Link>
    );
  }

  // Compact variant (default)
  return (
    <div className="flex items-center gap-3.5 rounded-sm border border-line bg-surface p-4">
      <Link href={`/m/${maker.handle}`}>
        <MakerAvatar maker={maker} size={48} />
      </Link>
      <div className="flex min-w-0 flex-1 flex-col">
        <Link href={`/m/${maker.handle}`} className="font-serif text-body font-medium text-text hover:text-brand truncate">
          {maker.name}
        </Link>
        <p className="text-caption text-muted truncate">{maker.place}</p>
        <p className="text-caption text-peacock-700 font-semibold mt-0.5">
          {maker.passport.state === "verified" ? "✓ Verified Karu Passport" : "Karu Passport"}
        </p>
      </div>
      <div className="shrink-0">
        <FollowButton artisanId={maker.id} initial={maker.following} />
      </div>
    </div>
  );
}
