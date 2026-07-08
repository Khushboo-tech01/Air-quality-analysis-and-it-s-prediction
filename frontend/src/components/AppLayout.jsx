import { Link, NavLink, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import {
  ChartLine, House, UploadSimple, Brain, Compass, FileText, Users, Wind,
  Sun, Moon, SignOut, ChartPieSlice,
} from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Toaster } from "sonner";

const NAV = [
  { to: "/dashboard", label: "Dashboard",   icon: House,        testid: "nav-dashboard" },
  { to: "/upload",    label: "Datasets",    icon: UploadSimple, testid: "nav-datasets" },
  { to: "/train",     label: "Train Models",icon: Brain,        testid: "nav-train" },
  { to: "/predict",   label: "Predict AQI", icon: Compass,      testid: "nav-predict" },
  { to: "/reports",   label: "Reports",     icon: FileText,     testid: "nav-reports" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const nav = useNavigate();

  const onLogout = async () => { await logout(); nav("/"); };

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      {/* Sidebar */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-border bg-card">
        <Link to="/dashboard" className="flex items-center gap-2 px-5 py-5 border-b border-border" data-testid="brand-link">
          <div className="h-8 w-8 rounded-md bg-primary text-primary-foreground flex items-center justify-center">
            <Wind size={20} weight="fill" />
          </div>
          <span className="font-display text-lg font-bold tracking-tight">AeroPulse</span>
        </Link>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              data-testid={n.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-primary/10 text-primary font-semibold" : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`
              }
            >
              <n.icon size={18} weight="regular" />
              {n.label}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              data-testid="nav-admin"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-primary/10 text-primary font-semibold" : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`
              }
            >
              <ChartPieSlice size={18} />
              Admin
            </NavLink>
          )}
        </nav>
        <div className="border-t border-border p-3 space-y-2">
          <div className="flex items-center gap-2 rounded-md px-2 py-2">
            <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center font-semibold text-sm">
              {user?.name?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium" data-testid="user-name">{user?.name || "User"}</p>
              <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline" size="sm" className="flex-1"
              data-testid="theme-toggle"
              onClick={toggle}
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
              <span className="ml-1.5">{theme === "dark" ? "Light" : "Dark"}</span>
            </Button>
            <Button variant="ghost" size="sm" onClick={onLogout} data-testid="logout-btn" className="text-muted-foreground">
              <SignOut size={16} />
            </Button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* Mobile top bar */}
        <div className="md:hidden flex items-center justify-between border-b border-border px-4 py-3 aq-glass sticky top-0 z-40">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-md bg-primary text-primary-foreground flex items-center justify-center">
              <Wind size={16} weight="fill" />
            </div>
            <span className="font-display text-base font-bold">AeroPulse</span>
          </Link>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={toggle} data-testid="theme-toggle-mobile">
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </Button>
            <Button variant="ghost" size="sm" onClick={onLogout}><SignOut size={16} /></Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </main>
      <Toaster position="top-right" richColors />
    </div>
  );
}
