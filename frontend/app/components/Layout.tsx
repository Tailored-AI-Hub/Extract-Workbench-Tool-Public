'use client'

import ChangePasswordModal from "./ChangePasswordModal";
import Sidebar from "./Sidebar";
import { ErrorBoundary } from "./ErrorBoundary";
import { useSidebar } from "../contexts/SidebarContext";

const Layout = ({ children }: { children: React.ReactNode }) => {
  const { collapsed } = useSidebar();
  
  return (
    <div className="min-h-screen bg-background flex overflow-hidden">
      <Sidebar />
      <div 
        className="flex-1 min-w-0 h-screen overflow-y-auto transition-all"
        style={{ marginLeft: collapsed ? '56px' : '240px' }}
      >
        <ErrorBoundary>
          <main className="w-full min-w-0">{children}</main>
        </ErrorBoundary>
      </div>
    </div>
  );
};

export default Layout;
