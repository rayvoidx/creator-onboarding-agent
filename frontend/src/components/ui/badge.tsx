import * as React from "react";
import { cn } from "../../lib/utils";

const badgeVariants: Record<string, string> = {
  default: "bg-accent/20 text-accent px-3 py-1",
  success: "bg-emerald-500/20 text-emerald-300 px-3 py-1",
  warning: "bg-amber-500/20 text-amber-300 px-3 py-1",
};

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: keyof typeof badgeVariants;
}

export function Badge({
  className,
  variant = "default",
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full text-xs font-semibold tracking-wide",
        badgeVariants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

