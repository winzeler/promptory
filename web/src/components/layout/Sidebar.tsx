import { Link, useLocation } from "react-router-dom";
import { useOrgs, useApps } from "../../hooks/usePrompts";
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
        <Link to="/" className="text-xl font-bold text-gray-900">
          Promptory
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
        Promptory v0.1.0
      </div>
    </aside>
  );
}
