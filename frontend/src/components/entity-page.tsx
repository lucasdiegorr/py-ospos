"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { DataTable, type Column } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Plus, Search, Pencil, Trash2 } from "lucide-react";

export interface FormFieldProps<T> {
  data: Partial<T>;
  onChange: (data: Partial<T>) => void;
  errors: Record<string, string>;
}

interface EntityPageProps<T> {
  title: string;
  apiPath: string;
  columns: Column<T>[];
  formFields: (props: {
    data: Partial<T>;
    onChange: (data: Partial<T>) => void;
    errors: Record<string, string>;
  }) => React.ReactNode;
  defaultFormData: Partial<T>;
  serializeForm: (data: Partial<T>) => Record<string, unknown>;
  idField?: keyof T;
}

export function EntityPage<T>({
  title,
  apiPath,
  columns,
  formFields,
  defaultFormData,
  serializeForm,
  idField = "id" as keyof T,
}: EntityPageProps<T>) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<T>>(defaultFormData);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        skip: String(page * 10),
        limit: "10",
      };
      if (search) params.search = search;
      const result = await api.list<T>(apiPath, params);
      setItems(result);
      setTotalPages(Math.ceil((result as unknown as { total?: number }).total ?? 1));
    } finally {
      setLoading(false);
    }
  }, [apiPath, page, search]);

  useEffect(() => {
    load();
  }, [load]);

  const handleOpenCreate = () => {
    setEditingId(null);
    setFormData(defaultFormData);
    setErrors({});
    setModalOpen(true);
  };

  const handleOpenEdit = (item: T) => {
    setEditingId(String(item[idField]));
    setFormData(item as unknown as Partial<T>);
    setErrors({});
    setModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setErrors({});
    try {
      if (editingId) {
        await api.update(apiPath, editingId, serializeForm(formData));
      } else {
        await api.create(apiPath, serializeForm(formData));
      }
      setModalOpen(false);
      load();
    } catch (err) {
      if (err instanceof Error) {
        try {
          const detail = JSON.parse(err.message);
          if (typeof detail === "object") {
            setErrors(detail);
          } else {
            setErrors({ form: err.message });
          }
        } catch {
          setErrors({ form: err.message });
        }
      } else {
        setErrors({ form: "An error occurred" });
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(apiPath, id);
      setDeleteConfirm(null);
      load();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const actionColumn: Column<T> = {
    header: "Actions",
    accessor: (item: T) => (
      <div className="flex gap-2">
        <button
          onClick={() => handleOpenEdit(item)}
          className="p-1.5 rounded-md text-muted hover:text-accent hover:bg-accent/10 transition-colors"
          title="Edit"
        >
          <Pencil size={16} />
        </button>
        <button
          onClick={() => setDeleteConfirm(String(item[idField]))}
          className="p-1.5 rounded-md text-muted hover:text-danger hover:bg-danger/10 transition-colors"
          title="Delete"
        >
          <Trash2 size={16} />
        </button>
      </div>
    ),
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{title}</h1>
        <Button onClick={handleOpenCreate}>
          <Plus size={18} />
          Add {title.slice(0, -1)}
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search
          size={18}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-surface text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50"
        />
      </div>

      <DataTable<T>
        columns={[...columns, actionColumn]}
        data={items}
        pageCount={totalPages}
        pageIndex={page}
        onPageChange={setPage}
        loading={loading}
      />

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingId ? `Edit ${title.slice(0, -1)}` : `Add ${title.slice(0, -1)}`}
      >
        <div className="space-y-4">
          {errors.form && (
            <p className="text-sm text-danger bg-danger/10 rounded-lg px-3 py-2">
              {errors.form}
            </p>
          )}
          {formFields({
            data: formData,
            onChange: setFormData,
            errors,
          })}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : editingId ? "Update" : "Create"}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        open={deleteConfirm !== null}
        onClose={() => setDeleteConfirm(null)}
        title="Confirm Delete"
      >
        <p className="text-muted mb-6">
          Are you sure you want to delete this {title.slice(0, -1).toLowerCase()}?
          This action cannot be undone.
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeleteConfirm(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteConfirm && handleDelete(deleteConfirm)}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}
