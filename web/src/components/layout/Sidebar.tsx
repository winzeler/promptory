import { Link, useLocation } from "react-router-dom";
import OrgAppSelector from "./OrgAppSelector";

const navItems = [
  { path: "/", label: "Dashboard", icon: "grid" },
  { path: "/sync", label: "Sync Status", icon: "refresh" },
  { path: "/settings/api-keys", label: "API Keys", icon: "key" },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="flex w-64 flex-col border-r border-gray-200 bg-white">
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-gray-200 px-4">
        <Link to="/" className="flex items-center gap-2 text-xl font-bold text-gray-900">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" className="h-7 w-7">
            <circle cx="32" cy="32" r="30" fill="#1f2937" />
            <polyline points="22,20 10,32 22,44" fill="none" stroke="#f9fafb" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
            <polyline points="42,20 54,32 42,44" fill="none" stroke="#f9fafb" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
            <polygon points="36,14 26,34 33,34 28,50 38,30 31,30" fill="#3b82f6" />
          </svg>
          Promptdis
        </Link>
      </div>

      {/* Org/App Selector */}
      <div className="border-b border-gray-200 p-4">
        <OrgAppSelector />
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center rounded-md px-3 py-2 text-sm font-medium ${
                isActive
                  ? "bg-gray-100 text-gray-900"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Version */}
      <div className="border-t border-gray-200 p-4 text-xs text-gray-400">
        Promptdis v0.1.0
      </div>
    </aside>
  );
}
