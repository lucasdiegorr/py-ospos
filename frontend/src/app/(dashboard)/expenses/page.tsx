"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { DataTable, type Column } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { TextField, NumberField, SelectField } from "@/components/ui/form-fields";
import { Plus, Search, Pencil, Trash2 } from "lucide-react";

interface Expense {
  id: string;
  description: string;
  amount: number;
  category_id?: string;
  is_recurring: boolean;
  reference_number?: string;
}

interface ExpenseCategory {
  id: string;
  name: string;
}

export default function ExpensesPage() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    description: "",
    amount: 0,
    category_id: "",
    reference_number: "",
    is_recurring: false,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        skip: String(page * 10),
        limit: "10",
        ...(search ? { search } : {}),
      };
      const result = await api.list<Expense>("expenses", params);
      setExpenses(result);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api.list<ExpenseCategory>("expenses/categories").then(setCategories).catch(() => {});
  }, []);

  const handleOpenCreate = () => {
    setEditingId(null);
    setForm({ description: "", amount: 0, category_id: "", reference_number: "", is_recurring: false });
    setErrors({});
    setModalOpen(true);
  };

  const handleOpenEdit = (item: Expense) => {
    setEditingId(item.id);
    setForm({
      description: item.description ?? "",
      amount: item.amount,
      category_id: item.category_id ?? "",
      reference_number: item.reference_number ?? "",
      is_recurring: item.is_recurring,
    });
    setErrors({});
    setModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setErrors({});
    try {
      const payload = {
        description: form.description || null,
        amount: form.amount,
        category_id: form.category_id || null,
        reference_number: form.reference_number || null,
        is_recurring: form.is_recurring,
      };
      if (editingId) {
        await api.update("expenses", editingId, payload);
      } else {
        await api.create("expenses", payload);
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
      await api.delete("expenses", id);
      setDeleteConfirm(null);
      load();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const columns: Column<Expense>[] = [
    { header: "Description", accessor: (e) => e.description ?? "—" },
    {
      header: "Amount",
      accessor: (e) => `$${e.amount.toFixed(2)}`,
      className: "font-mono",
    },
    {
      header: "Category",
      accessor: (e) =>
        categories.find((c) => c.id === e.category_id)?.name ?? "—",
    },
    { header: "Reference #", accessor: (e) => e.reference_number ?? "—" },
    {
      header: "Recurring",
      accessor: (e) => (e.is_recurring ? "Yes" : "No"),
    },
    {
      header: "Actions",
      accessor: (e) => (
        <div className="flex gap-2">
          <button
            onClick={() => handleOpenEdit(e)}
            className="p-1.5 rounded-md text-muted hover:text-accent hover:bg-accent/10 transition-colors"
          >
            <Pencil size={16} />
          </button>
          <button
            onClick={() => setDeleteConfirm(e.id)}
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
        <h1 className="text-2xl font-bold">Expenses</h1>
        <Button onClick={handleOpenCreate}>
          <Plus size={18} />
          Add Expense
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-surface text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50"
        />
      </div>

      <DataTable<Expense>
        columns={columns}
        data={expenses}
        pageCount={totalPages}
        pageIndex={page}
        onPageChange={setPage}
        loading={loading}
      />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editingId ? "Edit Expense" : "Add Expense"}>
        <div className="space-y-4">
          {errors.form && (
            <p className="text-sm text-danger bg-danger/10 rounded-lg px-3 py-2">{errors.form}</p>
          )}
          <TextField label="Description" value={form.description} onChange={(v) => setForm({ ...form, description: v })} />
          <NumberField label="Amount *" value={form.amount} onChange={(v) => setForm({ ...form, amount: v })} />
          <SelectField
            label="Category"
            value={form.category_id}
            onChange={(v) => setForm({ ...form, category_id: v })}
            options={categories.map((c) => ({ value: c.id, label: c.name }))}
          />
          <TextField label="Reference #" value={form.reference_number} onChange={(v) => setForm({ ...form, reference_number: v })} />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_recurring}
              onChange={(e) => setForm({ ...form, is_recurring: e.target.checked })}
              className="rounded border-border"
            />
            Recurring expense
          </label>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? "Saving..." : editingId ? "Update" : "Create"}</Button>
          </div>
        </div>
      </Modal>

      <Modal open={deleteConfirm !== null} onClose={() => setDeleteConfirm(null)} title="Confirm Delete">
        <p className="text-muted mb-6">Are you sure you want to delete this expense? This action cannot be undone.</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => deleteConfirm && handleDelete(deleteConfirm)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}
