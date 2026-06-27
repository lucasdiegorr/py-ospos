"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { DataTable, type Column } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { TextField, NumberField, SelectField } from "@/components/ui/form-fields";
import { Plus, Search, Pencil, Trash2 } from "lucide-react";

interface Item {
  id: string;
  name: string;
  cost_price: number;
  unit_price: number;
  quantity: number;
  is_active: boolean;
  category_id?: string;
  description?: string;
  sku?: string;
}

interface Category {
  id: string;
  name: string;
}

export default function ItemsPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    name: "",
    description: "",
    sku: "",
    category_id: "",
    cost_price: 0,
    unit_price: 0,
    quantity: 0,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { skip: String(page * 10), limit: "10" };
      if (search) params.search = search;
      const result = await api.list<Item>("items", params);
      setItems(result);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api.list<Category>("items/categories").then(setCategories).catch(() => {});
  }, []);

  const handleOpenCreate = () => {
    setEditingId(null);
    setForm({ name: "", description: "", sku: "", category_id: "", cost_price: 0, unit_price: 0, quantity: 0 });
    setErrors({});
    setModalOpen(true);
  };

  const handleOpenEdit = (item: Item) => {
    setEditingId(item.id);
    setForm({
      name: item.name,
      description: item.description ?? "",
      sku: item.sku ?? "",
      category_id: item.category_id ?? "",
      cost_price: item.cost_price,
      unit_price: item.unit_price,
      quantity: item.quantity,
    });
    setErrors({});
    setModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setErrors({});
    try {
      const payload = {
        name: form.name,
        description: form.description || null,
        sku: form.sku || null,
        category_id: form.category_id || null,
        cost_price: form.cost_price,
        unit_price: form.unit_price,
        quantity: form.quantity,
      };
      if (editingId) {
        await api.update("items", editingId, payload);
      } else {
        await api.create("items", payload);
      }
      setModalOpen(false);
      load();
    } catch (err) {
      setErrors({ form: err instanceof Error ? err.message : "An error occurred" });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete("items", id);
      setDeleteConfirm(null);
      load();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const columns: Column<Item>[] = [
    { header: "Name", accessor: (i) => i.name },
    { header: "SKU", accessor: (i) => i.sku ?? "—" },
    {
      header: "Cost",
      accessor: (i) => `$${i.cost_price.toFixed(2)}`,
      className: "font-mono",
    },
    {
      header: "Price",
      accessor: (i) => `$${i.unit_price.toFixed(2)}`,
      className: "font-mono",
    },
    {
      header: "Qty",
      accessor: (i) => i.quantity,
      className: "font-mono",
    },
    {
      header: "Status",
      accessor: (i) =>
        i.is_active ? (
          <span className="text-success">Active</span>
        ) : (
          <span className="text-muted">Inactive</span>
        ),
    },
    {
      header: "Actions",
      accessor: (i) => (
        <div className="flex gap-2">
          <button
            onClick={() => handleOpenEdit(i)}
            className="p-1.5 rounded-md text-muted hover:text-accent hover:bg-accent/10 transition-colors"
          >
            <Pencil size={16} />
          </button>
          <button
            onClick={() => setDeleteConfirm(i.id)}
            className="p-1.5 rounded-md text-muted hover:text-danger hover:bg-danger/10 transition-colors"
          >
            <Trash2 size={16} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Items</h1>
        <Button onClick={handleOpenCreate}>
          <Plus size={18} />
          Add Item
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          type="text"
          placeholder="Search items..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-surface text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50"
        />
      </div>

      <DataTable<Item>
        columns={columns}
        data={items}
        pageCount={totalPages}
        pageIndex={page}
        onPageChange={setPage}
        loading={loading}
      />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editingId ? "Edit Item" : "Add Item"}>
        <div className="space-y-4">
          {errors.form && (
            <p className="text-sm text-danger bg-danger/10 rounded-lg px-3 py-2">{errors.form}</p>
          )}
          <TextField label="Name *" value={form.name} onChange={(v) => setForm({ ...form, name: v })} error={errors.name} />
          <TextField label="Description" value={form.description} onChange={(v) => setForm({ ...form, description: v })} />
          <TextField label="SKU" value={form.sku} onChange={(v) => setForm({ ...form, sku: v })} />
          <SelectField
            label="Category"
            value={form.category_id}
            onChange={(v) => setForm({ ...form, category_id: v })}
            options={categories.map((c) => ({ value: c.id, label: c.name }))}
          />
          <div className="grid grid-cols-2 gap-4">
            <NumberField label="Cost Price" value={form.cost_price} onChange={(v) => setForm({ ...form, cost_price: v })} />
            <NumberField label="Unit Price" value={form.unit_price} onChange={(v) => setForm({ ...form, unit_price: v })} />
          </div>
          <NumberField label="Quantity" value={form.quantity} onChange={(v) => setForm({ ...form, quantity: v })} step="1" />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? "Saving..." : editingId ? "Update" : "Create"}</Button>
          </div>
        </div>
      </Modal>

      <Modal open={deleteConfirm !== null} onClose={() => setDeleteConfirm(null)} title="Confirm Delete">
        <p className="text-muted mb-6">Are you sure you want to delete this item? This action cannot be undone.</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => deleteConfirm && handleDelete(deleteConfirm)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}
