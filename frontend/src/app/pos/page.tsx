"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api, type SaleDetail, type SaleLine, type ItemResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Search, Plus, Minus, Trash2, ShoppingCart, X, Receipt, RotateCcw } from "lucide-react";

export default function PosPage() {
  const [cart, setCart] = useState<SaleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ItemResponse[]>([]);
  const [searching, setSearching] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [receiptOpen, setReceiptOpen] = useState(false);
  const [receipt, setReceipt] = useState<SaleDetail | null>(null);
  const [suspendOpen, setSuspendOpen] = useState(false);
  const [suspendedSales, setSuspendedSales] = useState<SaleDetail[]>([]);
  const [payment, setPayment] = useState({ type: "cash", amount: 0 });
  const [saving, setSaving] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // --- Load or create cart ---
  const loadCart = useCallback(async () => {
    try {
      let currentCart = await api.getCart();
      if (!currentCart) {
        currentCart = await api.createCart();
      }
      setCart(currentCart);
    } catch (err) {
      console.error("Failed to load cart", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCart();
  }, [loadCart]);

  // --- Item search (debounced) ---
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await api.list<ItemResponse>("items", {
          search: searchQuery,
          limit: "20",
        });
        setSearchResults(results);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => { if (searchTimer.current) clearTimeout(searchTimer.current); };
  }, [searchQuery]);

  // --- Add item to cart ---
  const handleAddItem = async (item: ItemResponse) => {
    try {
      const updatedCart = await api.addToCart({
        item_id: item.id,
        item_name: item.name,
        unit_price: item.unit_price,
        quantity: 1,
      });
      setCart(updatedCart);
    } catch (err) {
      console.error("Failed to add item", err);
    }
  };

  // --- Update quantity ---
  const handleUpdateQty = async (line: SaleLine, newQty: number) => {
    if (newQty < 1) return;
    try {
      const updatedCart = await api.updateCartItem({
        line_id: line.id,
        quantity: newQty,
      });
      setCart(updatedCart);
    } catch (err) {
      console.error("Failed to update quantity", err);
    }
  };

  // --- Remove item ---
  const handleRemoveItem = async (lineId: string) => {
    try {
      await api.removeFromCart(lineId);
      const updatedCart = await api.getCart();
      setCart(updatedCart);
    } catch (err) {
      console.error("Failed to remove item", err);
    }
  };

  // --- Checkout ---
  const handleCheckout = async () => {
    if (!cart || cart.lines.length === 0) return;
    setSaving(true);
    try {
      const completed = await api.completeSale({
        payments: [{ payment_type: payment.type, amount: payment.amount || cart.total }],
      });
      setReceipt(completed);
      setReceiptOpen(true);
      setCheckoutOpen(false);
      setCart(await api.createCart());
    } catch (err) {
      console.error("Checkout failed", err);
      alert(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setSaving(false);
    }
  };

  // --- Suspend ---
  const handleSuspend = async () => {
    if (!cart || cart.lines.length === 0) return;
    setSaving(true);
    try {
      await api.suspendSale();
      setSuspendOpen(false);
      setCart(await api.createCart());
    } catch (err) {
      console.error("Suspend failed", err);
      alert(err instanceof Error ? err.message : "Failed to suspend sale");
    } finally {
      setSaving(false);
    }
  };

  // --- Recall ---
  const handleRecall = async (saleId: string) => {
    try {
      const recalled = await api.recallSale(saleId);
      setCart(recalled);
      setSuspendOpen(false);
      setSuspendedSales([]);
    } catch (err) {
      console.error("Recall failed", err);
      alert(err instanceof Error ? err.message : "Failed to recall sale");
    }
  };

  // --- Load suspended sales for modal ---
  const openSuspendModal = async () => {
    setSuspendOpen(true);
    try {
      const sales = await api.getSuspendedSales();
      setSuspendedSales(sales);
    } catch {
      setSuspendedSales([]);
    }
  };

  // --- Handle barcode (Enter key on search) ---
  const handleSearchKeyDown = async (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && searchQuery.trim()) {
      try {
        const item = await api.lookupBarcode(searchQuery.trim());
        handleAddItem(item);
        setSearchQuery("");
      } catch {
        // Not a barcode, search results will handle it
      }
    }
  };

  // --- Calculate change ---
  const change = payment.amount - (cart?.total ?? 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent" />
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Left: Item search */}
      <div className="w-80 lg:w-96 border-r border-border flex flex-col bg-surface shrink-0">
        <div className="p-3 border-b border-border">
          <div className="relative">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              ref={searchRef}
              type="text"
              placeholder="Search items or scan barcode..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-background text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50 text-sm"
              autoFocus
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {searching && (
            <p className="text-sm text-muted text-center py-4">Searching...</p>
          )}
          {!searching && searchQuery && searchResults.length === 0 && (
            <p className="text-sm text-muted text-center py-4">No items found</p>
          )}
          {!searchQuery && (
            <p className="text-sm text-muted text-center py-4">
              Type to search items
            </p>
          )}
          {searchResults.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                handleAddItem(item);
                setSearchQuery("");
              }}
              className="w-full text-left p-3 rounded-lg hover:bg-background transition-colors border border-transparent hover:border-border"
            >
              <p className="font-medium text-sm">{item.name}</p>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-muted">
                  Stock: {item.quantity}
                  {item.is_below_reorder_level && (
                    <span className="text-danger ml-1">(low)</span>
                  )}
                </span>
                <span className="font-mono text-sm font-semibold text-success">
                  ${item.unit_price.toFixed(2)}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Center: Cart */}
      <div className="flex-1 flex flex-col min-w-0">
        {!cart || cart.lines.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-2">
              <ShoppingCart size={48} className="mx-auto text-muted" />
              <p className="text-muted">Cart is empty</p>
              <p className="text-sm text-muted">
                Search and select items to add
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {cart.lines.map((line) => (
                <div
                  key={line.id}
                  className="flex items-center gap-3 p-3 rounded-lg border border-border bg-surface"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">
                      {line.item_name}
                    </p>
                    <p className="font-mono text-sm text-success">
                      ${line.unit_price.toFixed(2)} ea
                    </p>
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleUpdateQty(line, line.quantity - 1)}
                      className="p-1 rounded-md hover:bg-background transition-colors text-muted hover:text-foreground"
                    >
                      <Minus size={16} />
                    </button>
                    <span className="w-8 text-center font-mono text-sm">
                      {line.quantity}
                    </span>
                    <button
                      onClick={() => handleUpdateQty(line, line.quantity + 1)}
                      className="p-1 rounded-md hover:bg-background transition-colors text-muted hover:text-foreground"
                    >
                      <Plus size={16} />
                    </button>
                  </div>

                  <p className="w-24 text-right font-mono text-sm font-semibold">
                    ${line.line_total.toFixed(2)}
                  </p>

                  <button
                    onClick={() => handleRemoveItem(line.id)}
                    className="p-1.5 rounded-md text-muted hover:text-danger hover:bg-danger/10 transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>

            {/* Totals bar */}
            <div className="border-t border-border bg-surface p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted">Subtotal</span>
                <span className="font-mono">${cart.subtotal.toFixed(2)}</span>
              </div>
              {cart.discount_amount > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Discount</span>
                  <span className="font-mono text-danger">
                    -${cart.discount_amount.toFixed(2)}
                  </span>
                </div>
              )}
              <div className="flex justify-between text-lg font-bold border-t border-border pt-2">
                <span>Total</span>
                <span className="font-mono text-success">
                  ${cart.total.toFixed(2)}
                </span>
              </div>

              <div className="flex gap-2 pt-2">
                <Button
                  className="flex-1"
                  onClick={() => {
                    setPayment({ type: "cash", amount: cart.total });
                    setCheckoutOpen(true);
                  }}
                >
                  Checkout
                </Button>
                <Button
                  variant="secondary"
                  onClick={openSuspendModal}
                >
                  Suspend
                </Button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Checkout modal */}
      <Modal
        open={checkoutOpen}
        onClose={() => setCheckoutOpen(false)}
        title="Complete Sale"
      >
        <div className="space-y-4">
          <p className="text-lg font-bold font-mono text-success">
            Total: ${cart?.total.toFixed(2)}
          </p>

          <div>
            <label className="block text-sm font-medium mb-1">
              Payment Type
            </label>
            <select
              value={payment.type}
              onChange={(e) => setPayment({ ...payment, type: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
            >
              <option value="cash">Cash</option>
              <option value="card">Card</option>
              <option value="check">Check</option>
              <option value="mobile">Mobile Payment</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Amount Tendered
            </label>
            <input
              type="number"
              step="0.01"
              value={payment.amount}
              onChange={(e) =>
                setPayment({ ...payment, amount: parseFloat(e.target.value) || 0 })
              }
              className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50 font-mono"
            />
          </div>

          {payment.amount >= (cart?.total ?? 0) && (
            <div className="flex justify-between text-sm">
              <span className="text-muted">Change</span>
              <span className="font-mono font-semibold text-success">
                ${change.toFixed(2)}
              </span>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => setCheckoutOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCheckout}
              disabled={saving || payment.amount < (cart?.total ?? 0)}
            >
              {saving ? "Processing..." : "Complete Sale"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Receipt modal */}
      <Modal
        open={receiptOpen}
        onClose={() => setReceiptOpen(false)}
        title="Sale Complete"
      >
        {receipt && (
          <div className="space-y-4">
            <div className="text-center">
              <Receipt size={32} className="mx-auto text-success mb-2" />
              <p className="text-sm text-muted">Sale #{receipt.id.slice(0, 8)}</p>
            </div>

            <div className="border-t border-border pt-3 space-y-2">
              {receipt.lines.map((line) => (
                <div key={line.id} className="flex justify-between text-sm">
                  <span>
                    {line.item_name} × {line.quantity}
                  </span>
                  <span className="font-mono">
                    ${line.line_total.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>

            <div className="border-t border-border pt-3 space-y-1">
              <div className="flex justify-between font-bold">
                <span>Total</span>
                <span className="font-mono text-success">
                  ${receipt.total.toFixed(2)}
                </span>
              </div>
              {receipt.payments.map((p, i) => (
                <div key={i} className="flex justify-between text-sm text-muted">
                  <span>Paid ({p.payment_type})</span>
                  <span className="font-mono">${p.amount.toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div className="flex justify-center pt-2">
              <Button onClick={() => setReceiptOpen(false)}>
                New Sale
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Suspend / Recall modal */}
      <Modal
        open={suspendOpen}
        onClose={() => setSuspendOpen(false)}
        title="Suspend & Recall Sales"
      >
        <div className="space-y-4">
          {cart && cart.lines.length > 0 && (
            <div>
              <p className="text-sm text-muted mb-3">
                Current cart has {cart.lines.length} item(s). What would you like to do?
              </p>
              <Button
                onClick={handleSuspend}
                disabled={saving}
                className="w-full"
              >
                <RotateCcw size={18} />
                Suspend Current Sale
              </Button>
            </div>
          )}

          <div className="border-t border-border pt-4">
            <p className="text-sm font-medium mb-3">Suspended Sales</p>
            {suspendedSales.length === 0 ? (
              <p className="text-sm text-muted">No suspended sales</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {suspendedSales.map((sale) => (
                  <div
                    key={sale.id}
                    className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-surface-hover transition-colors"
                  >
                    <div>
                      <p className="text-sm font-medium">
                        Sale #{sale.id.slice(0, 8)}
                      </p>
                      <p className="text-xs text-muted">
                        {sale.lines.length} item(s) — ${sale.total.toFixed(2)}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleRecall(sale.id)}
                    >
                      Recall
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end pt-2">
            <Button
              variant="secondary"
              onClick={() => setSuspendOpen(false)}
            >
              Close
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
