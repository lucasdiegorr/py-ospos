"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { DataTable, type Column } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Eye, Search } from "lucide-react";

interface Invoice {
  id: string;
  invoice_number: string;
  customer_id?: string;
  status: string;
  total: number;
  balance_due: number;
  created_at: string;
}

interface InvoiceDetail extends Invoice {
  lines: InvoiceLine[];
  payments: InvoicePayment[];
  comment?: string;
}

interface InvoiceLine {
  id: string;
  item_name: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

interface InvoicePayment {
  id: string;
  payment_type: string;
  amount: number;
}

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [detail, setDetail] = useState<InvoiceDetail | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { skip: String(page * 10), limit: "10" };
      if (search) params.search = search;
      const result = await api.list<Invoice>("invoices", params);
      setInvoices(result);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  const handleView = async (id: string) => {
    try {
      const inv = await api.get<InvoiceDetail>("invoices", id);
      setDetail(inv);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to load invoice");
    }
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      draft: "bg-muted text-muted-foreground",
      sent: "bg-accent/10 text-accent",
      paid: "bg-success/10 text-success",
      voided: "bg-danger/10 text-danger",
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? "bg-muted text-muted-foreground"}`}>
        {status}
      </span>
    );
  };

  const columns: Column<Invoice>[] = [
    { header: "Invoice #", accessor: (i) => i.invoice_number, className: "font-mono" },
    { header: "Status", accessor: (i) => statusBadge(i.status) },
    { header: "Total", accessor: (i) => `$${i.total.toFixed(2)}`, className: "font-mono" },
    { header: "Balance", accessor: (i) => `$${i.balance_due.toFixed(2)}`, className: "font-mono" },
    {
      header: "Date",
      accessor: (i) => new Date(i.created_at).toLocaleDateString(),
    },
    {
      header: "Actions",
      accessor: (i) => (
        <button
          onClick={() => handleView(i.id)}
          className="p-1.5 rounded-md text-muted hover:text-accent hover:bg-accent/10 transition-colors"
        >
          <Eye size={16} />
        </button>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Invoices</h1>
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

      <DataTable<Invoice>
        columns={columns}
        data={invoices}
        pageCount={totalPages}
        pageIndex={page}
        onPageChange={setPage}
        loading={loading}
      />

      <Modal open={detail !== null} onClose={() => setDetail(null)} title={`Invoice ${detail?.invoice_number ?? ""}`}>
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

            {detail.comment && (
              <div>
                <p className="text-sm text-muted mb-1">Comment</p>
                <p className="text-sm">{detail.comment}</p>
              </div>
            )}

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

            {detail.payments.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">Payments</p>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2">Type</th>
                      <th className="text-right py-2">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.payments.map((p) => (
                      <tr key={p.id} className="border-b border-border/50">
                        <td className="py-2">{p.payment_type}</td>
                        <td className="text-right py-2 font-mono">${p.amount.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex justify-end">
              <Button variant="secondary" onClick={() => setDetail(null)}>Close</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
