import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import Sidebar from "./components/layout/Sidebar";
import Header from "./components/layout/Header";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import PromptBrowserPage from "./pages/PromptBrowserPage";
import PromptEditorPage from "./pages/PromptEditorPage";
import PromptPreviewPage from "./pages/PromptPreviewPage";
import EvaluationPage from "./pages/EvaluationPage";
import AppSettingsPage from "./pages/AppSettingsPage";
import ApiKeysPage from "./pages/ApiKeysPage";
import SyncStatusPage from "./pages/SyncStatusPage";

function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-lg text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route
        path="/"
        element={
          <AuthenticatedLayout>
            <DashboardPage />
          </AuthenticatedLayout>
        }
      />
      <Route
        path="/apps/:appId/prompts"
        element={
          <AuthenticatedLayout>
            <PromptBrowserPage />
          </AuthenticatedLayout>
        }
      />
      <Route
        path="/prompts/:id/edit"
        element={
          <AuthenticatedLayout>
            <PromptEditorPage />
          </AuthenticatedLayout>
        }
      />
      <Route
        path="/prompts/:id/preview"
        element={
          <AuthenticatedLayout>
            <PromptPreviewPage />
          </AuthenticatedLayout>
        }
      />
      <Route
        path="/prompts/:id/eval"
        element={
          <AuthenticatedLayout>
            <EvaluationPage />
          </AuthenticatedLayout>
        }
      />
      <Route
        path="/apps/:appId/settings"
        element={
          <AuthenticatedLayout>
            <AppSettingsPage />
          </AuthenticatedLayout>
        }
      />
      <Route
        path="/settings/api-keys"
        element={
          <AuthenticatedLayout>
            <ApiKeysPage />
          </AuthenticatedLayout>
        }
      />
      <Route
        path="/sync"
        element={
          <AuthenticatedLayout>
            <SyncStatusPage />
          </AuthenticatedLayout>
        }
      />
    </Routes>
  );
}
