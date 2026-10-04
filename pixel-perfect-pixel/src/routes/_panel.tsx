import { Outlet, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAuth } from "@/features/auth/AuthContext";

export const Route = createFileRoute("/_panel")({
  component: PanelLayout,
});

function PanelLayout() {
  const { usuario, cargando } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!cargando && !usuario) {
      navigate({ to: "/login" });
    }
  }, [cargando, usuario, navigate]);

  if (cargando || !usuario) {
    return <div className="min-h-screen bg-background" />;
  }

  return (
    <div className="flex min-h-screen w-full bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
