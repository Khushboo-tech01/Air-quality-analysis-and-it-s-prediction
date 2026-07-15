import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import AppLayout from "@/components/AppLayout";
import ProtectedRoute from "@/components/ProtectedRoute";
import { Toaster } from "sonner";

import Dashboard     from "@/pages/Dashboard";
import Predict       from "@/pages/Predict";
import Reports       from "@/pages/Reports";
import Admin         from "@/pages/Admin";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Account from "@/pages/Account";
import Legal from "@/pages/Legal";

function BootGate({ children }) {
  const { loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <p className="text-sm text-muted-foreground">Loading workspace…</p>
        </div>
      </div>
    );
  }
  return children;
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <BootGate>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/about" element={<Legal page="about" />} />
              <Route path="/contact" element={<Legal page="contact" />} />
              <Route path="/faq" element={<Legal page="faq" />} />
              <Route path="/privacy" element={<Legal page="privacy" />} />
              <Route path="/terms" element={<Legal page="terms" />} />
              <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/dashboard"    element={<Dashboard />} />
                <Route path="/upload"       element={<Navigate to="/predict" replace />} />
                <Route path="/dataset/:id"  element={<Navigate to="/predict" replace />} />
                <Route path="/train"        element={<Navigate to="/predict" replace />} />
                <Route path="/predict"      element={<Predict />} />
                <Route path="/reports"      element={<Reports />} />
                <Route path="/admin"        element={<Admin />} />
                <Route path="/account"      element={<Account />} />
              </Route>
              </Route>
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </BootGate>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </ThemeProvider>
  );
}
