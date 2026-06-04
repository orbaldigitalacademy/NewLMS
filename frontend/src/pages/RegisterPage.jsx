import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const next = searchParams.get("next") || "/dashboard";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await register(name, email, password);
      toast.success(`Welcome to Atlas Academy, ${user.name.split(" ")[0]}`);
      navigate(next);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="register-page" className="max-w-[1100px] mx-auto px-6 md:px-10 lg:px-16 py-16 grid grid-cols-1 md:grid-cols-12 gap-12">
      <div className="md:col-span-5 hidden md:block">
        <div className="eyebrow mb-6">Apply</div>
        <h1 className="font-display text-5xl tracking-tighter leading-none mb-6">
          Begin a deliberate practice.
        </h1>
        <p className="text-[color:var(--text-muted)] leading-relaxed">
          Free to register. Some courses are free, others are seasonal cohorts with paid access. Either way—your learning is yours forever.
        </p>
      </div>
      <form onSubmit={onSubmit} className="md:col-span-7 border border-black/10 bg-white p-8 md:p-12">
        <h2 className="font-display text-3xl mb-8">Create your account</h2>
        <label className="eyebrow block mb-2">Full name</label>
        <input
          data-testid="register-name-input"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input-line mb-6"
          placeholder="Your name"
        />
        <label className="eyebrow block mb-2">Email</label>
        <input
          data-testid="register-email-input"
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
          data-testid="register-password-input"
          type="password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="input-line mb-8"
          placeholder="Min. 6 characters"
        />
        <button data-testid="register-submit-btn" disabled={loading} className="btn-primary w-full justify-center">
          {loading ? "Creating account…" : "Create account"}
        </button>
        <p className="text-sm text-[color:var(--text-muted)] mt-6">
          Have an account?{" "}
          <Link to="/login" className="editorial-link text-[color:var(--accent)]">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
