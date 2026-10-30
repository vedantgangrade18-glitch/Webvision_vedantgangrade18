import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { SpotArt } from "@/components/karu/ornaments";
import { Button } from "@/components/ui/button";

export default async function NotFound() {
  const t = await getTranslations("errors_page");
  return (
    <main className="mx-auto flex min-h-[75vh] max-w-md flex-col items-center justify-center gap-5 px-6 text-center">
      <SpotArt name="thread" className="size-20 text-brand" />
      <div>
        <h1 className="font-serif text-h1 text-ink-900">
          This thread came loose
        </h1>
        <p className="text-body text-muted mt-2">
          {t("not_found_body") || "We couldn't find the page you're looking for. It may have moved or no longer exists."}
        </p>
      </div>
      <Link href="/">
        <Button variant="primary" size="L">
          {t("home") || "Back to Karu Home"}
        </Button>
      </Link>
    </main>
  );
}
