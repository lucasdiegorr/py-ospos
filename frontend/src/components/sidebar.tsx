"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShoppingCart,
  Package,
  Users,
  UserCircle,
  Wallet,
  FileText,
  Sun,
  Moon,
  LogOut,
  LayoutDashboard,
} from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, admin: false },
  { href: "/pos", label: "Point of Sale", icon: ShoppingCart, admin: false },
  { href: "/customers", label: "Customers", icon: Users, admin: true },
  { href: "/items", label: "Items", icon: Package, admin: true },
  { href: "/employees", label: "Employees", icon: UserCircle, admin: true },
  { href: "/expenses", label: "Expenses", icon: Wallet, admin: true },
  { href: "/invoices", label: "Invoices", icon: FileText, admin: true },
  { href: "/quotations", label: "Quotations", icon: FileText, admin: true },
];

interface SidebarProps {
  isAdmin: boolean;
  onLogout: () => void;
}

export function Sidebar({ isAdmin, onLogout }: SidebarProps) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const visibleItems = navItems.filter((item) => !item.admin || isAdmin);

  return (
    <aside className="hidden lg:flex lg:flex-col w-60 border-r border-border bg-surface h-full">
      <div className="p-4 border-b border-border">
        <Link href="/" className="text-lg font-bold tracking-tight">
          py-ospos
        </Link>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-foreground hover:bg-surface-hover"
              }`}
            >
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-border space-y-1">
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-foreground hover:bg-surface-hover transition-colors"
        >
          {mounted && theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          {mounted && theme === "dark" ? "Light Mode" : "Dark Mode"}
        </button>
        <button
          onClick={onLogout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-danger hover:bg-surface-hover transition-colors"
        >
          <LogOut size={18} />
          Logout
        </button>
      </div>
    </aside>
  );
}
