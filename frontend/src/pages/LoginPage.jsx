import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const next = searchParams.get("next") || "/dashboard";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await login(email, password);
      toast.success(`Welcome back, ${user.name.split(" ")[0]}`);
      navigate(next);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="login-page" className="max-w-[1100px] mx-auto px-6 md:px-10 lg:px-16 py-16 grid grid-cols-1 md:grid-cols-12 gap-12">
      <div className="md:col-span-5 hidden md:block">
        <div className="eyebrow mb-6">Sign in</div>
        <h1 className="font-display text-5xl tracking-tighter leading-none mb-6">
          Welcome back to the studio.
        </h1>
        <p className="text-[color:var(--text-muted)] leading-relaxed">
          Pick up where you left off. Your enrollments, progress, and certificates are saved.
        </p>
      </div>
      <form onSubmit={onSubmit} className="md:col-span-7 border border-black/10 bg-white p-8 md:p-12 max-w-md md:max-w-none">
        <h2 className="font-display text-3xl mb-8">Sign in</h2>
        <label className="eyebrow block mb-2">Email</label>
        <input
          data-testid="login-email-input"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="input-line mb-6"
          placeholder="you@studio.com"
        />
        <label className="eyebrow block mb-2">Password</label>
        <input
          data-testid="login-password-input"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="input-line mb-8"
          placeholder="••••••••"
        />
        <button data-testid="login-submit-btn" disabled={loading} className="btn-primary w-full justify-center">
          {loading ? "Signing in…" : "Sign in"}
        </button>
        <p className="text-sm text-[color:var(--text-muted)] mt-6">
          New here?{" "}
          <Link to="/register" className="editorial-link text-[color:var(--accent)]">
            Create an account
          </Link>
        </p>
        <div className="mt-8 border-t border-black/10 pt-5 text-xs text-[color:var(--text-muted)] font-mono">
          Try: admin@atlasacademy.io / admin123 — or — student@atlasacademy.io / student123
        </div>
      </form>
    </div>
  );
}
