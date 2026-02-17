import { useAuth } from "../../hooks/useAuth";

export default function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div />
      <div className="flex items-center gap-4">
        {user && (
          <>
            <div className="flex items-center gap-2">
              {user.avatar_url && (
                <img
                  src={user.avatar_url}
                  alt={user.github_login}
                  className="h-7 w-7 rounded-full"
                />
              )}
              <span className="text-sm text-gray-700">{user.display_name || user.github_login}</span>
            </div>
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Sign out
            </button>
          </>
        )}
      </div>
    </header>
  );
}
