import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth, roleAtLeast } from "@/auth";
import { Button } from "@/components/ui/button";

type SidebarItem = { to: string; label: string };

export function Sidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const isManager = roleAtLeast(user, "manager");

  const items: SidebarItem[] = [
    { to: "/pos", label: "PDV" },
    { to: "/customers", label: "Clientes" },
    { to: "/products", label: "Produtos" },
    { to: "/shift", label: "Caixa" },
    ...(isManager ? [{ to: "/reports", label: "Relatórios" }] : []),
  ];

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={onClose}
          aria-hidden
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-card border-r border-border transition-transform duration-200",
          "md:sticky md:top-16 md:h-[calc(100vh-4rem)] md:translate-x-0 md:z-30",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center justify-between px-4 border-b border-border md:hidden">
          <span className="text-sm font-semibold">py-ospos</span>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Fechar menu"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-foreground hover:bg-accent hover:text-accent-foreground",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}

export function AppLayout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="flex flex-1 flex-col min-w-0">{children}</div>
    </div>
  );
}
