import { Link } from "react-router-dom";
import { GraduationCap } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-black/10 bg-[#F8F6F0] mt-24">
      <div className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-16 grid grid-cols-1 md:grid-cols-12 gap-8">
        <div className="md:col-span-5">
          <div className="flex items-center gap-2 mb-4">
            <GraduationCap strokeWidth={1.5} className="w-6 h-6 text-[color:var(--accent)]" />
            <span className="font-display text-3xl">Atlas Academy</span>
          </div>
          <p className="text-sm text-[color:var(--text-muted)] max-w-md leading-relaxed">
            A modern learning studio for designers, engineers and product builders.
            Independent, opinionated, and made for serious craft.
          </p>
        </div>

        <div className="md:col-span-2">
          <div className="eyebrow mb-4">Learn</div>
          <ul className="flex flex-col gap-2 text-sm">
            <li>
              <Link to="/courses" className="editorial-link">Catalog</Link>
            </li>
            <li>
              <Link to="/dashboard" className="editorial-link">Dashboard</Link>
            </li>
          </ul>
        </div>

        <div className="md:col-span-2">
          <div className="eyebrow mb-4">Studio</div>
          <ul className="flex flex-col gap-2 text-sm">
            <li>
              <Link to="/contact" className="editorial-link">Contact</Link>
            </li>
            <li>
              <Link to="/register" className="editorial-link">Apply</Link>
            </li>
          </ul>
        </div>

        <div className="md:col-span-3">
          <div className="eyebrow mb-4">Office</div>
          <p className="text-sm text-[color:var(--text-muted)]">
            Plot 12, Idejo Street<br />
            Victoria Island, Lagos<br />
            studio@atlasacademy.io
          </p>
        </div>
      </div>
      <div className="border-t border-black/10">
        <div className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-6 flex flex-col md:flex-row justify-between items-center text-xs text-[color:var(--text-muted)]">
          <span>© {new Date().getFullYear()} Atlas Academy. All rights reserved.</span>
          <span className="font-mono">Made with discipline · Lagos / Remote</span>
        </div>
      </div>
    </footer>
  );
}
