import { useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Send } from "lucide-react";

export default function ContactPage() {
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/contacts", form);
      toast.success("Message sent. We'll be in touch within two business days.");
      setForm({ name: "", email: "", subject: "", message: "" });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to send");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="contact-page" className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-16 grid grid-cols-1 md:grid-cols-12 gap-12">
      <div className="md:col-span-5">
        <div className="eyebrow mb-5">Get in touch</div>
        <h1 className="font-display text-5xl sm:text-6xl tracking-tighter leading-none mb-8">
          A short note goes a long way.
        </h1>
        <p className="text-[color:var(--text-muted)] leading-relaxed mb-10">
          For partnerships, corporate cohorts, press, or general questions—use the form, or reach us directly.
        </p>
        <div className="border-t border-black/10 pt-6 space-y-4 text-sm">
          <div>
            <div className="eyebrow mb-1">Studio</div>
            <p>studio@atlasacademy.io</p>
          </div>
          <div>
            <div className="eyebrow mb-1">Press</div>
            <p>press@atlasacademy.io</p>
          </div>
          <div>
            <div className="eyebrow mb-1">Office</div>
            <p>Plot 12, Idejo St. Victoria Island, Lagos</p>
          </div>
        </div>
      </div>

      <form onSubmit={onSubmit} className="md:col-span-7 border border-black/10 bg-white p-8 md:p-12">
        <h2 className="font-display text-3xl mb-8">Send a message</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <label className="eyebrow block mb-2">Name</label>
            <input data-testid="contact-name" required value={form.name} onChange={set("name")} className="input-line" />
          </div>
          <div>
            <label className="eyebrow block mb-2">Email</label>
            <input data-testid="contact-email" type="email" required value={form.email} onChange={set("email")} className="input-line" />
          </div>
        </div>
        <label className="eyebrow block mb-2">Subject</label>
        <input data-testid="contact-subject" value={form.subject} onChange={set("subject")} className="input-line mb-6" />
        <label className="eyebrow block mb-2">Message</label>
        <textarea
          data-testid="contact-message"
          required
          rows={6}
          value={form.message}
          onChange={set("message")}
          className="w-full bg-transparent border-b-2 border-[color:var(--border)] focus:border-[color:var(--accent)] outline-none py-2 mb-8 resize-y"
        />
        <button data-testid="contact-submit" disabled={loading} className="btn-primary">
          {loading ? "Sending…" : (
            <>
              Send message <Send className="w-4 h-4" strokeWidth={1.5} />
            </>
          )}
        </button>
      </form>
    </div>
  );
}
