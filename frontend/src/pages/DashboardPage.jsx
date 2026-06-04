import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Award, BookOpen, Download, TrendingUp } from "lucide-react";
import { toast } from "sonner";

export default function DashboardPage() {
  const { user } = useAuth();
  const [enrollments, setEnrollments] = useState([]);
  const [coursesById, setCoursesById] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data: ens } = await api.get("/enrollments/me");
        setEnrollments(ens);
        const courses = await Promise.all(
          ens.map((e) => api.get(`/courses/${e.course_id}`).then((r) => r.data).catch(() => null)),
        );
        const map = {};
        courses.forEach((c) => {
          if (c) map[c.id] = c;
        });
        setCoursesById(map);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const downloadCert = async (course_id, slug) => {
    try {
      const res = await api.get(`/enrollments/certificate/${course_id}`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `certificate-${slug || course_id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error("Certificate not available yet");
    }
  };

  const inProgress = enrollments.filter((e) => !e.is_completed);
  const completed = enrollments.filter((e) => e.is_completed);

  return (
    <div data-testid="dashboard-page" className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-12">
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 mb-12 items-end">
        <div className="md:col-span-8">
          <div className="eyebrow mb-3">Studio · Dashboard</div>
          <h1 className="font-display text-4xl sm:text-5xl tracking-tighter leading-none mb-2">
            Hello, {user?.name.split(" ")[0]}.
          </h1>
          <p className="text-[color:var(--text-muted)]">
            Pick up where you left off. Below are your enrollments, progress, and certificates.
          </p>
        </div>
        <div className="md:col-span-4 grid grid-cols-3 gap-3 border-l border-black/10 pl-6">
          <Stat label="Enrolled" value={enrollments.length} icon={BookOpen} />
          <Stat label="In progress" value={inProgress.length} icon={TrendingUp} />
          <Stat label="Completed" value={completed.length} icon={Award} />
        </div>
      </div>

      {loading ? (
        <div className="py-24 text-center eyebrow">Loading dashboard…</div>
      ) : enrollments.length === 0 ? (
        <div className="border border-black/10 bg-white p-12 text-center">
          <h3 className="font-display text-3xl mb-4">No enrollments yet.</h3>
          <p className="text-[color:var(--text-muted)] mb-8">Browse the catalog and pick your first course.</p>
          <Link to="/courses" data-testid="dashboard-browse-btn" className="btn-primary inline-flex">
            Browse Catalog
          </Link>
        </div>
      ) : (
        <>
          <section className="mb-16">
            <div className="eyebrow mb-5">In progress</div>
            {inProgress.length === 0 ? (
              <p className="text-[color:var(--text-muted)] py-6">Nothing in progress. Start something new!</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {inProgress.map((e) => {
                  const c = coursesById[e.course_id];
                  if (!c) return null;
                  return (
                    <div key={e.id} className="surface-card p-6" data-testid={`enrollment-card-${c.id}`}>
                      <div className="eyebrow mb-3 text-[color:var(--accent)]">{c.category}</div>
                      <h3 className="font-display text-2xl leading-tight mb-4">{c.title}</h3>
                      <div className="mb-5">
                        <div className="flex justify-between text-xs mb-2">
                          <span className="text-[color:var(--text-muted)]">Progress</span>
                          <span className="font-mono">{Math.round(e.progress)}%</span>
                        </div>
                        <div className="h-1 bg-black/10">
                          <div
                            className="h-full bg-[color:var(--accent)] transition-all"
                            style={{ width: `${e.progress}%` }}
                          />
                        </div>
                      </div>
                      <Link
                        to={`/learn/${c.id}`}
                        data-testid={`continue-btn-${c.id}`}
                        className="btn-ghost text-sm py-2 px-4"
                      >
                        Continue →
                      </Link>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {completed.length > 0 && (
            <section>
              <div className="eyebrow mb-5">Completed · Certificates</div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {completed.map((e) => {
                  const c = coursesById[e.course_id];
                  if (!c) return null;
                  return (
                    <div key={e.id} className="surface-card p-6 border-l-4 border-[color:var(--accent)]">
                      <Award className="w-7 h-7 text-[color:var(--accent)] mb-4" strokeWidth={1.5} />
                      <h3 className="font-display text-2xl leading-tight mb-2">{c.title}</h3>
                      <p className="text-xs text-[color:var(--text-muted)] mb-5">
                        Completed {e.completed_at ? new Date(e.completed_at).toLocaleDateString() : "—"}
                      </p>
                      <button
                        onClick={() => downloadCert(c.id, c.slug)}
                        data-testid={`download-cert-${c.id}`}
                        className="btn-primary text-sm py-2 px-4"
                      >
                        <Download className="w-4 h-4" strokeWidth={1.5} /> Certificate
                      </button>
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ label, value, icon: Icon }) {
  return (
    <div className="text-center">
      <Icon className="w-5 h-5 mx-auto mb-2 text-[color:var(--accent)]" strokeWidth={1.5} />
      <div className="font-display text-3xl">{value}</div>
      <div className="text-[10px] uppercase tracking-[0.18em] text-[color:var(--text-muted)] mt-1">{label}</div>
    </div>
  );
}
