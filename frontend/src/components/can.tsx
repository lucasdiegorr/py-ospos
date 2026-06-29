"use client";

import { type ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";

interface CanProps {
  permission: string;
  fallback?: ReactNode;
  children: ReactNode;
}

export function Can({ permission, fallback = null, children }: CanProps) {
  const { can } = useAuth();
  if (!can(permission)) return fallback;
  return <>{children}</>;
}
