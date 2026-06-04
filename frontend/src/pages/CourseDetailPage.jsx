import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { BookOpen, Clock, Layers, PlayCircle, Lock, CheckCircle2, ArrowRight } from "lucide-react";

export default function CourseDetailPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [course, setCourse] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [enrollment, setEnrollment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const { data: c } = await api.get(`/courses/slug/${slug}`).catch(() =>
          api.get(`/courses/${slug}`),
        );
        if (!active) return;
        setCourse(c);
        const { data: ls } = await api.get(`/lessons/by-course/${c.id}`);
        if (!active) return;
        setLessons(ls);
        if (user) {
          const { data: en } = await api.get(`/enrollments/check/${c.id}`);
          if (!active) return;
          setEnrollment(en.enrolled ? en.enrollment : null);
        }
      } catch {
        toast.error("Course not found");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [slug, user]);

  const onEnroll = async () => {
    if (!user) {
      navigate(`/login?next=/courses/${slug}`);
      return;
    }
    if (!course) return;
    setBusy(true);
    try {
      if (course.price <= 0) {
        const { data } = await api.post("/enrollments/free", { course_id: course.id });
        setEnrollment(data);
        toast.success("Enrolled! Start your first lesson.");
      } else {
        const callback_url = `${window.location.origin}/payment/callback`;
        const { data } = await api.post("/payments/initialize", {
          course_id: course.id,
          callback_url,
        });
        window.location.href = data.authorization_url;
        return;
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to enroll");
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <div className="py-32 text-center eyebrow">Loading course…</div>;
  }
  if (!course) return null;

  const totalMinutes = lessons.reduce((s, l) => s + (l.duration_minutes || 0), 0);

  return (
    <div data-testid="course-detail-page" className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-12 md:py-16">
      {/* Header */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 mb-16">
        <div className="lg:col-span-7 fade-up">
          <div className="eyebrow mb-5">
            <span className="text-[color:var(--accent)]">{course.category}</span> · {course.level}
          </div>
          <h1 className="font-display text-5xl sm:text-6xl tracking-tighter leading-[0.95] mb-6">
            {course.title}
          </h1>
          <p className="text-lg leading-relaxed text-[color:var(--text-muted)] mb-8 max-w-xl">
            {course.short_description}
          </p>
          <div className="flex flex-wrap items-center gap-6 text-sm text-[color:var(--text-muted)] mb-10">
            <span className="inline-flex items-center gap-2">
              <BookOpen className="w-4 h-4" strokeWidth={1.5} /> {lessons.length} lessons
            </span>
            <span className="inline-flex items-center gap-2">
              <Clock className="w-4 h-4" strokeWidth={1.5} /> {Math.max(1, Math.round(totalMinutes / 60))} hrs
            </span>
            <span className="inline-flex items-center gap-2">
              <Layers className="w-4 h-4" strokeWidth={1.5} /> {course.level}
            </span>
          </div>
          <div className="border-l-2 border-[color:var(--accent)] pl-5">
            <div className="eyebrow mb-1">Instructor</div>
            <p className="font-display text-2xl">{course.instructor_name}</p>
          </div>
        </div>

        <div className="lg:col-span-5 fade-up fade-up-2">
          <div className="border border-black/10 bg-white">
            <div className="aspect-[16/10] bg-[#1c1917] overflow-hidden">
              {course.thumbnail_url ? (
                <img src={course.thumbnail_url} alt={course.title} className="w-full h-full object-cover" />
              ) : null}
            </div>
            <div className="p-8">
              <div className="flex items-end justify-between mb-6">
                <div>
                  <div className="eyebrow mb-1">Price</div>
                  <div className="font-display text-4xl">
                    {course.price > 0 ? `₦${course.price.toLocaleString()}` : "Free"}
                  </div>
                </div>
                <div className="text-right">
                  <div className="eyebrow mb-1">Enrollment</div>
                  <div className="text-sm">{course.enrollment_count} students</div>
                </div>
              </div>

              {enrollment ? (
                <Link
                  to={`/learn/${course.id}`}
                  data-testid="continue-learning-btn"
                  className="btn-primary w-full justify-center"
                >
                  Continue learning <ArrowRight className="w-4 h-4" strokeWidth={1.5} />
                </Link>
              ) : (
                <button
                  data-testid="enroll-btn"
                  onClick={onEnroll}
                  disabled={busy}
                  className="btn-primary w-full justify-center"
                >
                  {busy ? "Processing…" : course.price > 0 ? "Enroll · Pay with Paystack" : "Enroll for Free"}
                </button>
              )}

              <p className="text-xs text-[color:var(--text-muted)] mt-4 leading-relaxed">
                {course.price > 0
                  ? "Lifetime access. Certificate on completion. Secure payment via Paystack."
                  : "Free, forever. Certificate on completion."}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* About */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-12 mb-16">
        <div className="lg:col-span-7">
          <div className="eyebrow mb-4">About this course</div>
          <p className="text-base md:text-lg leading-relaxed whitespace-pre-wrap text-[color:var(--text)]">
            {course.description}
          </p>
          {course.tags?.length > 0 && (
            <div className="mt-8 flex flex-wrap gap-2">
              {course.tags.map((t) => (
                <span key={t} className="text-xs uppercase tracking-wider px-3 py-1 border border-black/15 text-[color:var(--text-muted)]">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="lg:col-span-5">
          <div className="eyebrow mb-4">Curriculum</div>
          <ol className="border-t border-black/10">
            {lessons.map((l, i) => (
              <li
                key={l.id}
                data-testid={`curriculum-item-${l.id}`}
                className="border-b border-black/10 py-4 flex items-center justify-between gap-4"
              >
                <div className="flex items-start gap-4">
                  <span className="font-mono text-xs text-[color:var(--text-muted)] mt-1">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <div className="font-medium">{l.title}</div>
                    {l.description && (
                      <div className="text-xs text-[color:var(--text-muted)] mt-1">{l.description}</div>
                    )}
                  </div>
                </div>
                <div className="text-xs text-[color:var(--text-muted)] flex items-center gap-2 whitespace-nowrap">
                  {l.is_preview ? (
                    <PlayCircle className="w-4 h-4 text-[color:var(--accent)]" strokeWidth={1.5} />
                  ) : enrollment ? (
                    <CheckCircle2 className="w-4 h-4" strokeWidth={1.5} />
                  ) : (
                    <Lock className="w-4 h-4" strokeWidth={1.5} />
                  )}
                  {l.duration_minutes}m
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </div>
  );
}
