import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import AppLayout from "@/components/AppLayout";
import { Toaster } from "sonner";

import Landing       from "@/pages/Landing";
import Login         from "@/pages/Login";
import Register      from "@/pages/Register";
import Forgot        from "@/pages/Forgot";
import Dashboard     from "@/pages/Dashboard";
import Upload        from "@/pages/Upload";
import DatasetDetail from "@/pages/DatasetDetail";
import Train         from "@/pages/Train";
import Predict       from "@/pages/Predict";
import Reports       from "@/pages/Reports";
import Admin         from "@/pages/Admin";

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/"          element={<Landing />} />
            <Route path="/login"     element={<Login />} />
            <Route path="/register"  element={<Register />} />
            <Route path="/forgot"    element={<Forgot />} />

            <Route element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }>
              <Route path="/dashboard"         element={<Dashboard />} />
              <Route path="/upload"            element={<Upload />} />
              <Route path="/dataset/:id"       element={<DatasetDetail />} />
              <Route path="/train"             element={<Train />} />
              <Route path="/predict"           element={<Predict />} />
              <Route path="/reports"           element={<Reports />} />
              <Route path="/admin"             element={<ProtectedRoute adminOnly><Admin /></ProtectedRoute>} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </ThemeProvider>
  );
}
