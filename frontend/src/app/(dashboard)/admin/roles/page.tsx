"use client";

import { useEffect, useState } from "react";
import { api, type RoleBrief, type RoleDetail, type Permission } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Can } from "@/components/can";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

export default function RolesPage() {
  const { can } = useAuth();
  const [roles, setRoles] = useState<RoleBrief[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editRole, setEditRole] = useState<RoleDetail | null>(null);
  const [showDelete, setShowDelete] = useState<string | null>(null);

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const data = await api.listRoles();
      setRoles(data);
    } catch {
      setError("Failed to load roles");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (can("admin.roles")) fetchRoles();
    else setLoading(false);
  }, [can]);

  if (!can("admin.roles")) {
    return (
      <div className="p-6">
        <p className="text-muted">You do not have permission to manage roles.</p>
      </div>
    );
  }

  const handleDelete = async (roleId: string) => {
    try {
      await api.deleteRole(roleId);
      setRoles((prev) => prev.filter((r) => r.id !== roleId));
      setShowDelete(null);
    } catch {
      setError("Failed to delete role");
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Roles</h1>
        <Can permission="admin.roles">
          <Button onClick={() => setEditRole({ id: "", name: "", description: "", is_default: false, permissions: [] })}>
            Create Role
          </Button>
        </Can>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-danger/10 text-danger text-sm">{error}</div>
      )}

      {loading ? (
        <p className="text-muted">Loading...</p>
      ) : roles.length === 0 ? (
        <p className="text-muted">No roles found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-surface">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted">Name</th>
                <th className="px-4 py-3 text-left font-medium text-muted">Description</th>
                <th className="px-4 py-3 text-left font-medium text-muted">Permissions</th>
                <th className="px-4 py-3 text-right font-medium text-muted">Actions</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr key={role.id} className="border-t border-border hover:bg-surface/50 transition-colors">
                  <td className="px-4 py-3 font-medium">{role.name}</td>
                  <td className="px-4 py-3 text-muted">{role.description ?? "—"}</td>
                  <td className="px-4 py-3">{role.permission_count}</td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <Button variant="secondary" size="sm" onClick={() => loadRoleDetail(role.id)}>
                      Edit
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => setShowDelete(role.id)}>
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editRole && (
        <RoleFormModal
          role={editRole}
          onClose={() => setEditRole(null)}
          onSaved={() => { setEditRole(null); fetchRoles(); }}
          onError={setError}
        />
      )}

      {showDelete && (
        <Modal open={true} onClose={() => setShowDelete(null)} title="Delete Role">
          <p className="text-sm text-muted mb-4">Are you sure you want to delete this role? This action cannot be undone.</p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowDelete(null)}>Cancel</Button>
            <Button variant="danger" onClick={() => handleDelete(showDelete)}>Delete</Button>
          </div>
        </Modal>
      )}
    </div>
  );

  async function loadRoleDetail(id: string) {
    try {
      const detail = await api.getRole(id);
      setEditRole(detail);
    } catch {
      setError("Failed to load role details");
    }
  }
}

function RoleFormModal({
  role,
  onClose,
  onSaved,
  onError,
}: {
  role: RoleDetail;
  onClose: () => void;
  onSaved: () => void;
  onError: (msg: string) => void;
}) {
  const [name, setName] = useState(role.name);
  const [description, setDescription] = useState(role.description ?? "");
  const [permissionIds, setPermissionIds] = useState<string[]>(role.permissions.map((p) => p.id));
  const [allPermissions, setAllPermissions] = useState<Permission[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.listPermissions().then(setAllPermissions).catch(() => {});
  }, []);

  const isNew = !role.id;

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (isNew) {
        await api.createRole({ name: name.trim(), description: description || undefined, permission_ids: permissionIds });
      } else {
        await api.updateRole(role.id, { name: name.trim(), description: description || undefined, permission_ids: permissionIds });
      }
      onSaved();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to save role");
    } finally {
      setSaving(false);
    }
  };

  const togglePermission = (permId: string) => {
    setPermissionIds((prev) =>
      prev.includes(permId) ? prev.filter((id) => id !== permId) : [...prev, permId]
    );
  };

  return (
    <Modal open={true} onClose={onClose} title={isNew ? "Create Role" : "Edit Role"}>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
            placeholder="Role name"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
            placeholder="Optional description"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Permissions</label>
          <div className="max-h-60 overflow-y-auto space-y-1 border border-border rounded-lg p-2">
            {allPermissions.map((perm) => (
              <label key={perm.id} className="flex items-center gap-2 px-2 py-1 rounded hover:bg-surface-hover cursor-pointer text-sm">
                <input
                  type="checkbox"
                  checked={permissionIds.includes(perm.id)}
                  onChange={() => togglePermission(perm.id)}
                  className="rounded border-border"
                />
                <span className="font-mono text-xs text-muted">{perm.code}</span>
                <span className="text-foreground">{perm.name}</span>
              </label>
            ))}
            {allPermissions.length === 0 && (
              <p className="text-sm text-muted px-2 py-1">Loading permissions...</p>
            )}
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving || !name.trim()}>
            {saving ? "Saving..." : isNew ? "Create" : "Save"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
