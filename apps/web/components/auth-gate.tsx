"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { Spinner } from "@/components/ui";
import { useMe } from "@/lib/hooks";
import type { Me } from "@/lib/types";

/** Client-side guard: personalised pages render after /me resolves (with token refresh). */
export function AuthGate({ children, require }: { children: (me: Me) => ReactNode; require?: "artisan" | "staff" }) {
  const { data: me, isLoading } = useMe();
  const router = useRouter();
  const path = usePathname();
  useEffect(() => {
    if (isLoading) return;
    if (!me) router.replace(`/login?next=${encodeURIComponent(path)}`);
    else if (require === "artisan" && !me.has_artisan_profile) router.replace("/sell/start");
  }, [me, isLoading, router, path, require]);
  if (isLoading || !me || (require === "artisan" && !me.has_artisan_profile)) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner />
      </div>
    );
  }
  return <>{children(me)}</>;
}
