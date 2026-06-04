import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { CheckCircle2, XCircle } from "lucide-react";

export default function PaymentCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const reference = searchParams.get("reference") || searchParams.get("trxref");
  const [state, setState] = useState({ loading: true, success: false, message: "" });

  useEffect(() => {
    if (!reference) {
      setState({ loading: false, success: false, message: "No reference supplied." });
      return;
    }
    (async () => {
      try {
        const { data } = await api.get(`/payments/verify/${reference}`);
        if (data.status === "success") {
          setState({ loading: false, success: true, message: "Payment verified. You're enrolled!" });
          setTimeout(() => navigate("/dashboard"), 1500);
        } else {
          setState({ loading: false, success: false, message: data.message || "Payment was not completed." });
        }
      } catch (e) {
        setState({ loading: false, success: false, message: e?.response?.data?.detail || "Could not verify." });
      }
    })();
  }, [reference, navigate]);

  return (
    <div data-testid="payment-callback-page" className="max-w-[700px] mx-auto px-6 py-24 text-center">
      {state.loading ? (
        <>
          <div className="eyebrow mb-4">Paystack</div>
          <h1 className="font-display text-4xl mb-3">Verifying your payment…</h1>
          <p className="text-[color:var(--text-muted)]">Hold tight while we confirm with Paystack.</p>
        </>
      ) : state.success ? (
        <>
          <CheckCircle2 className="w-12 h-12 text-[color:var(--success)] mx-auto mb-6" strokeWidth={1.5} />
          <h1 className="font-display text-4xl mb-3">{state.message}</h1>
          <p className="text-[color:var(--text-muted)] mb-8">Taking you to your dashboard…</p>
          <Link to="/dashboard" className="btn-primary">Go to dashboard</Link>
        </>
      ) : (
        <>
          <XCircle className="w-12 h-12 text-[color:var(--error)] mx-auto mb-6" strokeWidth={1.5} />
          <h1 className="font-display text-4xl mb-3">Payment not completed</h1>
          <p className="text-[color:var(--text-muted)] mb-8">{state.message}</p>
          <Link to="/courses" className="btn-ghost">Back to catalog</Link>
        </>
      )}
    </div>
  );
}
