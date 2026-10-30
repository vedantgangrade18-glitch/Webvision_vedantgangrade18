import Link from "next/link";
import { ArrowRight } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface TextLinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  href: string;
  arrow?: boolean;
}

export function TextLink({
  href,
  children,
  arrow = false,
  className,
  ...rest
}: TextLinkProps) {
  return (
    <Link
      href={href}
      className={cx(
        "group inline-flex items-center gap-1.5 text-eyebrow text-brand hover:text-brand-hover underline-offset-4 hover:underline transition-colors",
        className
      )}
      {...rest}
    >
      <span>{children}</span>
      {arrow && (
        <ArrowRight className="size-3.5 flip-rtl transition-transform group-hover:translate-x-0.5 rtl:group-hover:-translate-x-0.5" />
      )}
    </Link>
  );
}
