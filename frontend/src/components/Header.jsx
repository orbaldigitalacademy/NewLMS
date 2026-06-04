import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { GraduationCap, LogOut, User as UserIcon, Menu, X } from "lucide-react";
import { useState } from "react";

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const onLogout = () => {
    logout();
    navigate("/");
  };

  const navLinkClass = ({ isActive }) =>
    `editorial-link text-sm tracking-wide ${isActive ? "border-b-2 border-[color:var(--accent)] text-[color:var(--accent)]" : ""}`;

  return (
    <header className="sticky top-0 z-40 bg-[#F8F6F0]/85 backdrop-blur-xl border-b border-black/5">
      <div className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 h-16 flex items-center justify-between">
        <Link to="/" data-testid="header-logo" className="flex items-center gap-2">
          <GraduationCap strokeWidth={1.5} className="w-6 h-6 text-[color:var(--accent)]" />
          <span className="font-display text-2xl tracking-tight">Atlas Academy</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8" aria-label="Primary">
          <NavLink to="/" data-testid="nav-home" className={navLinkClass} end>
            Home
          </NavLink>
          <NavLink to="/courses" data-testid="nav-courses" className={navLinkClass}>
            Courses
          </NavLink>
          <NavLink to="/contact" data-testid="nav-contact" className={navLinkClass}>
            Contact
          </NavLink>
          {user && (
            <NavLink to="/dashboard" data-testid="nav-dashboard" className={navLinkClass}>
              Dashboard
            </NavLink>
          )}
          {user?.role === "admin" && (
            <NavLink to="/admin" data-testid="nav-admin" className={navLinkClass}>
              Admin
            </NavLink>
          )}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <>
              <span className="eyebrow hidden lg:inline" data-testid="header-user-name">
                {user.name.split(" ")[0]}
              </span>
              <button
                onClick={onLogout}
                data-testid="header-logout-btn"
                className="btn-ghost text-sm py-2 px-4"
              >
                <LogOut className="w-4 h-4" strokeWidth={1.5} /> Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" data-testid="header-login-link" className="btn-ghost text-sm py-2 px-4">
                <UserIcon className="w-4 h-4" strokeWidth={1.5} /> Login
              </Link>
              <Link to="/register" data-testid="header-register-link" className="btn-primary text-sm py-2 px-4">
                Get Started
              </Link>
            </>
          )}
        </div>

        <button
          className="md:hidden p-2"
          onClick={() => setOpen((o) => !o)}
          data-testid="header-menu-toggle"
          aria-label="Toggle menu"
        >
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {open && (
        <div className="md:hidden border-t border-black/5 bg-[#F8F6F0]">
          <nav className="flex flex-col px-6 py-4 gap-4">
            <NavLink to="/" onClick={() => setOpen(false)} className="text-base">
              Home
            </NavLink>
            <NavLink to="/courses" onClick={() => setOpen(false)} className="text-base">
              Courses
            </NavLink>
            <NavLink to="/contact" onClick={() => setOpen(false)} className="text-base">
              Contact
            </NavLink>
            {user && (
              <NavLink to="/dashboard" onClick={() => setOpen(false)} className="text-base">
                Dashboard
              </NavLink>
            )}
            {user?.role === "admin" && (
              <NavLink to="/admin" onClick={() => setOpen(false)} className="text-base">
                Admin
              </NavLink>
            )}
            <div className="flex gap-2 pt-2">
              {user ? (
                <button onClick={onLogout} data-testid="mobile-logout-btn" className="btn-ghost flex-1 text-sm">
                  Logout
                </button>
              ) : (
                <>
                  <Link to="/login" className="btn-ghost flex-1 text-sm text-center" onClick={() => setOpen(false)}>
                    Login
                  </Link>
                  <Link to="/register" className="btn-primary flex-1 text-sm text-center" onClick={() => setOpen(false)}>
                    Get Started
                  </Link>
                </>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
