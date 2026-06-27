"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { DataTable, type Column } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { TextField } from "@/components/ui/form-fields";
import { Plus, Search, Pencil, Trash2, Eye } from "lucide-react";

interface Quotation {
  id: string;
  quotation_number: string;
  customer_id?: string;
  status: string;
  total: number;
  created_at: string;
  comment?: string;
}

interface QuotationDetail extends Quotation {
  lines: QuotationLine[];
  expires_at?: string;
}

interface QuotationLine {
  id: string;
  item_name: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export default function QuotationsPage() {
  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [detail, setDetail] = useState<QuotationDetail | null>(null);

  const [form, setForm] = useState({
    customer_id: "",
    comment: "",
    expires_at: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { skip: String(page * 10), limit: "10" };
      if (search) params.search = search;
      const result = await api.list<Quotation>("quotations", params);
      setQuotations(result);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  const handleOpenCreate = () => {
    setEditingId(null);
    setForm({ customer_id: "", comment: "", expires_at: "" });
    setErrors({});
    setModalOpen(true);
  };

  const handleOpenEdit = (item: Quotation) => {
    setEditingId(item.id);
    setForm({
      customer_id: item.customer_id ?? "",
      comment: item.comment ?? "",
      expires_at: "",
    });
    setErrors({});
    setModalOpen(true);
  };

  const handleViewDetail = async (id: string) => {
    try {
      const q = await api.get<QuotationDetail>("quotations", id);
      setDetail(q);
      setDetailOpen(true);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to load quotation");
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setErrors({});
    try {
      const payload: Record<string, unknown> = {
        customer_id: form.customer_id || null,
        comment: form.comment || null,
      };
      if (form.expires_at) payload.expires_at = form.expires_at;
      if (editingId) {
        await api.update("quotations", editingId, payload);
      } else {
        await api.create("quotations", payload);
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
      await api.delete("quotations", id);
      setDeleteConfirm(null);
      load();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      draft: "bg-muted text-muted-foreground",
      sent: "bg-accent/10 text-accent",
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? "bg-muted text-muted-foreground"}`}>
        {status}
      </span>
    );
  };

  const columns: Column<Quotation>[] = [
    { header: "Quote #", accessor: (q) => q.quotation_number, className: "font-mono" },
    { header: "Status", accessor: (q) => statusBadge(q.status) },
    { header: "Total", accessor: (q) => `$${q.total.toFixed(2)}`, className: "font-mono" },
    {
      header: "Date",
      accessor: (q) => new Date(q.created_at).toLocaleDateString(),
    },
    {
      header: "Actions",
      accessor: (q) => (
        <div className="flex gap-1">
          <button
            onClick={() => handleViewDetail(q.id)}
            className="p-1.5 rounded-md text-muted hover:text-accent hover:bg-accent/10 transition-colors"
            title="View"
          >
            <Eye size={16} />
          </button>
          {q.status === "draft" && (
            <>
              <button
                onClick={() => handleOpenEdit(q)}
                className="p-1.5 rounded-md text-muted hover:text-accent hover:bg-accent/10 transition-colors"
                title="Edit"
              >
                <Pencil size={16} />
              </button>
              <button
                onClick={() => setDeleteConfirm(q.id)}
                className="p-1.5 rounded-md text-muted hover:text-danger hover:bg-danger/10 transition-colors"
                title="Delete"
              >
                <Trash2 size={16} />
              </button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Quotations</h1>
        <Button onClick={handleOpenCreate}>
          <Plus size={18} />
          Add Quotation
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

      <DataTable<Quotation>
        columns={columns}
        data={quotations}
        pageCount={totalPages}
        pageIndex={page}
        onPageChange={setPage}
        loading={loading}
      />

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editingId ? "Edit Quotation" : "Add Quotation"}>
        <div className="space-y-4">
          {errors.form && <p className="text-sm text-danger bg-danger/10 rounded-lg px-3 py-2">{errors.form}</p>}
          <TextField label="Comment" value={form.comment} onChange={(v) => setForm({ ...form, comment: v })} />
          <TextField label="Expires At" value={form.expires_at} onChange={(v) => setForm({ ...form, expires_at: v })} placeholder="YYYY-MM-DD" />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? "Saving..." : editingId ? "Update" : "Create"}</Button>
          </div>
        </div>
      </Modal>

      <Modal open={deleteConfirm !== null} onClose={() => setDeleteConfirm(null)} title="Confirm Delete">
        <p className="text-muted mb-6">Are you sure you want to delete this quotation? This action cannot be undone.</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => deleteConfirm && handleDelete(deleteConfirm)}>Delete</Button>
        </div>
      </Modal>

      <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title={`Quotation ${detail?.quotation_number ?? ""}`}>
        {detail && (
          <div className="space-y-6">
            <div className="flex justify-between">
              <div className="space-y-1">
                <p className="text-sm text-muted">Status</p>
                {statusBadge(detail.status)}
              </div>
              <div className="text-right space-y-1">
                <p className="text-sm text-muted">Total</p>
                <p className="text-xl font-bold font-mono">${detail.total.toFixed(2)}</p>
              </div>
            </div>

            <div>
              <p className="text-sm font-medium mb-2">Line Items</p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2">Item</th>
                    <th className="text-right py-2">Qty</th>
                    <th className="text-right py-2">Price</th>
                    <th className="text-right py-2">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.lines.map((line) => (
                    <tr key={line.id} className="border-b border-border/50">
                      <td className="py-2">{line.item_name}</td>
                      <td className="text-right py-2 font-mono">{line.quantity}</td>
                      <td className="text-right py-2 font-mono">${line.unit_price.toFixed(2)}</td>
                      <td className="text-right py-2 font-mono">${line.line_total.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end">
              <Button variant="secondary" onClick={() => setDetailOpen(false)}>Close</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
