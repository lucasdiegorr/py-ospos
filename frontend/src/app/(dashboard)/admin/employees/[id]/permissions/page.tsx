"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { api, type RoleBrief, type Permission } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";

export default function EmployeePermissionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { can } = useAuth();

  const [assignedRoles, setAssignedRoles] = useState<RoleBrief[]>([]);
  const [allRoles, setAllRoles] = useState<RoleBrief[]>([]);
  const [effectivePermissions, setEffectivePermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!can("admin.roles")) {
      setLoading(false);
      return;
    }
    Promise.all([
      api.listRoles(),
      api.getEmployeeRoles(id),
    ])
      .then(([all, assigned]) => {
        setAllRoles(all);
        setAssignedRoles(assigned);
        const permCodes = assigned.flatMap((r) => r.permission_count > 0 ? [r.name] : []);
        return assigned;
      })
      .catch(() => setError("Failed to load data"))
      .finally(() => setLoading(false));

    api.listPermissions().then((perms) => {});
  }, [id, can]);

  useEffect(() => {
    if (!can("admin.roles") || assignedRoles.length === 0) {
      setEffectivePermissions([]);
      return;
    }
    const ids = assignedRoles.map((r) => r.id);
    if (ids.length === 0) { setEffectivePermissions([]); return; }

    const allPromises = ids.map((rid) =>
      api.getRole(rid).catch(() => null)
    );
    Promise.all(allPromises).then((details) => {
      const codes = new Set<string>();
      for (const d of details) {
        if (d) d.permissions.forEach((p) => codes.add(p.code));
      }
      setEffectivePermissions(Array.from(codes).sort());
    });
  }, [assignedRoles, can]);

  if (!can("admin.roles")) {
    return (
      <div className="p-6">
        <p className="text-muted">You do not have permission to manage employee permissions.</p>
      </div>
    );
  }

  const isAssigned = (roleId: string) => assignedRoles.some((r) => r.id === roleId);

  const toggleRole = (roleId: string) => {
    setAssignedRoles((prev) =>
      isAssigned(roleId) ? prev.filter((r) => r.id !== roleId) : [...prev, allRoles.find((r) => r.id === roleId)!]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const roleIds = assignedRoles.map((r) => r.id);
      await api.assignEmployeeRoles(id, roleIds);
    } catch {
      setError("Failed to save role assignments");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => router.back()} className="text-sm text-muted hover:text-foreground mb-1">&larr; Back</button>
          <h1 className="text-2xl font-bold">Employee Permissions</h1>
          <p className="text-sm text-muted">Employee ID: {id}</p>
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Changes"}
        </Button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-danger/10 text-danger text-sm">{error}</div>
      )}

      {loading ? (
        <p className="text-muted">Loading...</p>
      ) : (
        <>
          <div className="rounded-lg border border-border">
            <div className="px-4 py-3 bg-surface font-medium text-sm border-b border-border">
              Assign Roles
            </div>
            <div className="divide-y divide-border">
              {allRoles.length === 0 ? (
                <p className="px-4 py-3 text-sm text-muted">No roles available.</p>
              ) : (
                allRoles.map((role) => (
                  <label key={role.id} className="flex items-center gap-3 px-4 py-3 hover:bg-surface/50 cursor-pointer transition-colors">
                    <input
                      type="checkbox"
                      checked={isAssigned(role.id)}
                      onChange={() => toggleRole(role.id)}
                      className="rounded border-border"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-sm">{role.name}</div>
                      <div className="text-xs text-muted">{role.description ?? "—"}</div>
                    </div>
                    <span className="text-xs text-muted">{role.permission_count} permissions</span>
                  </label>
                ))
              )}
            </div>
          </div>

          <div className="rounded-lg border border-border">
            <div className="px-4 py-3 bg-surface font-medium text-sm border-b border-border">
              Effective Permissions
            </div>
            <div className="px-4 py-3">
              {effectivePermissions.length === 0 ? (
                <p className="text-sm text-muted">No permissions granted by assigned roles.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {effectivePermissions.map((code) => (
                    <span key={code} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent/10 text-accent-foreground">
                      {code}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
