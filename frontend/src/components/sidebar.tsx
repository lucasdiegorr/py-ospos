"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShoppingCart, Package, Users, UserCircle, Wallet, FileText,
  Sun, Moon, LogOut, LayoutDashboard, Shield,
} from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";

interface NavSection {
  label: string | null;
  items: { href: string; label: string; icon: React.ComponentType<{ size?: number }>; perm: string | null }[];
}

const navSections: NavSection[] = [
  {
    label: null,
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard, perm: null },
      { href: "/pos", label: "Point of Sale", icon: ShoppingCart, perm: null },
      { href: "/customers", label: "Customers", icon: Users, perm: "customers.read" },
      { href: "/items", label: "Items", icon: Package, perm: "items.read" },
      { href: "/employees", label: "Employees", icon: UserCircle, perm: "employees.read" },
      { href: "/expenses", label: "Expenses", icon: Wallet, perm: "expenses.read" },
      { href: "/invoices", label: "Invoices", icon: FileText, perm: "invoices.read" },
      { href: "/quotations", label: "Quotations", icon: FileText, perm: "quotations.read" },
    ],
  },
  {
    label: "Admin",
    items: [
      { href: "/admin/roles", label: "Roles", icon: Shield, perm: "admin.roles" },
    ],
  },
];

interface SidebarProps {
  onLogout: () => void;
}

export function Sidebar({ onLogout }: SidebarProps) {
  const { can } = useAuth();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <aside className="hidden lg:flex lg:flex-col w-60 border-r border-border bg-surface h-full">
      <div className="p-4 border-b border-border">
        <Link href="/" className="text-lg font-bold tracking-tight">py-ospos</Link>
      </div>
      <nav className="flex-1 p-3 overflow-y-auto">
        {navSections.map((section) => {
          const visibleItems = section.items.filter((item) => !item.perm || can(item.perm));
          if (visibleItems.length === 0) return null;
          return (
            <div key={section.label ?? "__main"} className="mb-4 last:mb-0">
              {section.label && (
                <p className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-muted">
                  {section.label}
                </p>
              )}
              <div className="space-y-0.5">
                {visibleItems.map((item) => {
                  const Icon = item.icon;
                  const active = pathname === item.href;
                  return (
                    <Link key={item.href} href={item.href}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        active ? "bg-accent text-accent-foreground" : "text-foreground hover:bg-surface-hover"
                      }`}
                    >
                      <Icon size={18} />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>
      <div className="p-3 border-t border-border space-y-1">
        {mounted && (
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-foreground hover:bg-surface-hover transition-colors"
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            {theme === "dark" ? "Light Mode" : "Dark Mode"}
          </button>
        )}
        <button
          onClick={onLogout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-foreground hover:bg-surface-hover transition-colors"
        >
          <LogOut size={18} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
