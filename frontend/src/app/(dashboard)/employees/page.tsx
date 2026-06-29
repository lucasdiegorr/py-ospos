"use client";

import { useAuth } from "@/lib/auth-context";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { UserCircle, Shield, Mail, Phone } from "lucide-react";

export default function EmployeesPage() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">My Profile</h1>

      <Card className="max-w-md">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-full bg-accent/10 text-accent">
              <UserCircle size={32} />
            </div>
            <div>
              <CardTitle>{user.username}</CardTitle>
              <p className="text-sm text-muted">Employee</p>
            </div>
          </div>
        </CardHeader>
        <div className="px-6 pb-6 space-y-3">
          <div className="flex items-center gap-2 text-sm">
            <Shield size={16} className="text-muted" />
            <span>{user.permissions.length} permission(s)</span>
          </div>
        </div>
      </Card>

      <div className="p-4 rounded-lg border border-border bg-surface max-w-md">
        <p className="text-sm text-muted">
          Full employee management requires a backend list endpoint. This page shows
          the current user&apos;s profile.
        </p>
      </div>
    </div>
  );
}
