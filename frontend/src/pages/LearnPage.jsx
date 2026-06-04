import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";
import { CheckCircle2, Circle, ChevronLeft, ChevronRight, FileText, Lock } from "lucide-react";

function isYouTube(url) {
  return /youtube\.com|youtu\.be/.test(url || "");
}

function toEmbedUrl(url) {
  if (!url) return null;
  if (url.includes("youtube.com/embed")) return url;
  const m = url.match(/(?:youtu\.be\/|v=)([\w-]{6,})/);
  if (m) return `https://www.youtube.com/embed/${m[1]}`;
  return url;
}

export default function LearnPage() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [enrollment, setEnrollment] = useState(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [{ data: c }, { data: ls }, { data: en }] = await Promise.all([
          api.get(`/courses/${courseId}`),
          api.get(`/lessons/by-course/${courseId}`),
          api.get(`/enrollments/check/${courseId}`),
        ]);
        if (!en.enrolled) {
          toast.error("Enroll in this course first.");
          navigate(`/courses/${c.slug || c.id}`);
          return;
        }
        setCourse(c);
        setLessons(ls);
        setEnrollment(en.enrollment);
      } catch {
        toast.error("Could not load course");
      } finally {
        setLoading(false);
      }
    })();
  }, [courseId, navigate]);

  const active = lessons[activeIdx];
  const completedSet = useMemo(
    () => new Set(enrollment?.completed_lessons || []),
    [enrollment],
  );

  const markComplete = async () => {
    if (!active) return;
    try {
      const { data } = await api.post("/enrollments/progress", { lesson_id: active.id });
      setEnrollment(data);
      if (data.is_completed) {
        toast.success("Course complete! Certificate is ready.");
      } else {
        toast.success("Lesson marked complete.");
      }
    } catch {
      toast.error("Failed to update progress");
    }
  };

  if (loading) return <div className="py-32 text-center eyebrow">Loading lesson…</div>;
  if (!course || lessons.length === 0)
    return <div className="py-32 text-center eyebrow">No lessons yet.</div>;

  const embed = toEmbedUrl(active.video_url);
  const isCompleted = completedSet.has(active.id);

  return (
    <div data-testid="learn-page" className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-8 md:py-12">
      <div className="mb-6 flex items-center gap-3">
        <Link to={`/courses/${course.slug || course.id}`} className="editorial-link text-sm">
          ← Back to course
        </Link>
        <span className="text-[color:var(--text-muted)] text-sm">/</span>
        <span className="font-display text-xl">{course.title}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Video + content */}
        <div className="lg:col-span-8">
          <div className="aspect-video bg-black border border-black/10 overflow-hidden">
            {active.video_url ? (
              isYouTube(active.video_url) ? (
                <iframe
                  data-testid="lesson-video-iframe"
                  src={embed}
                  className="w-full h-full"
                  allowFullScreen
                  title={active.title}
                />
              ) : (
                <video
                  data-testid="lesson-video-player"
                  src={active.video_url}
                  controls
                  className="w-full h-full"
                />
              )
            ) : (
              <div className="w-full h-full flex items-center justify-center text-white/70 font-display text-2xl">
                Text-only lesson
              </div>
            )}
          </div>

          <div className="mt-6 border-b border-black/10 pb-6 flex items-start justify-between gap-6 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <div className="eyebrow mb-2">Lesson {activeIdx + 1} / {lessons.length}</div>
              <h1 className="font-display text-3xl sm:text-4xl tracking-tight leading-tight">
                {active.title}
              </h1>
              {active.description && (
                <p className="text-[color:var(--text-muted)] mt-2">{active.description}</p>
              )}
            </div>
            <button
              data-testid="mark-complete-btn"
              onClick={markComplete}
              className={isCompleted ? "btn-ghost" : "btn-primary"}
            >
              {isCompleted ? (
                <>
                  <CheckCircle2 className="w-4 h-4" strokeWidth={1.5} /> Completed
                </>
              ) : (
                "Mark as complete"
              )}
            </button>
          </div>

          {active.content_text && (
            <div className="mt-8 prose prose-stone max-w-none">
              <div className="eyebrow mb-3">Notes</div>
              <p className="text-base leading-relaxed whitespace-pre-wrap">{active.content_text}</p>
            </div>
          )}

          {active.resources?.length > 0 && (
            <div className="mt-8">
              <div className="eyebrow mb-3">Resources</div>
              <ul className="border-t border-black/10">
                {active.resources.map((r, i) => (
                  <li key={i} className="border-b border-black/10 py-3">
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      data-testid={`resource-${i}`}
                      className="editorial-link inline-flex items-center gap-2 text-sm"
                    >
                      <FileText className="w-4 h-4" strokeWidth={1.5} /> {r.name}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-10 flex justify-between border-t border-black/10 pt-6">
            <button
              data-testid="prev-lesson-btn"
              onClick={() => setActiveIdx((i) => Math.max(0, i - 1))}
              disabled={activeIdx === 0}
              className="btn-ghost text-sm disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" strokeWidth={1.5} /> Previous
            </button>
            <button
              data-testid="next-lesson-btn"
              onClick={() => setActiveIdx((i) => Math.min(lessons.length - 1, i + 1))}
              disabled={activeIdx >= lessons.length - 1}
              className="btn-primary text-sm disabled:opacity-40"
            >
              Next <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
            </button>
          </div>
        </div>

        {/* Sidebar */}
        <aside className="lg:col-span-4">
          <div className="border border-black/10 bg-white">
            <div className="p-5 border-b border-black/10">
              <div className="eyebrow mb-2">Progress</div>
              <div className="flex justify-between text-sm mb-2">
                <span>{completedSet.size} / {lessons.length} complete</span>
                <span className="font-mono">{Math.round(enrollment?.progress || 0)}%</span>
              </div>
              <div className="h-1 bg-black/10">
                <div
                  className="h-full bg-[color:var(--accent)] transition-all"
                  style={{ width: `${enrollment?.progress || 0}%` }}
                />
              </div>
            </div>
            <ol className="max-h-[60vh] overflow-y-auto">
              {lessons.map((l, i) => {
                const done = completedSet.has(l.id);
                return (
                  <li key={l.id}>
                    <button
                      data-testid={`sidebar-lesson-${l.id}`}
                      onClick={() => setActiveIdx(i)}
                      className={`w-full text-left p-4 border-b border-black/5 flex items-start gap-3 hover:bg-[var(--bg)] transition-colors ${i === activeIdx ? "bg-[var(--bg)] border-l-4 border-l-[color:var(--accent)]" : ""}`}
                    >
                      <span className="mt-0.5">
                        {done ? (
                          <CheckCircle2 className="w-4 h-4 text-[color:var(--success)]" strokeWidth={1.5} />
                        ) : (
                          <Circle className="w-4 h-4 text-[color:var(--text-muted)]" strokeWidth={1.5} />
                        )}
                      </span>
                      <span className="flex-1">
                        <span className="block font-medium text-sm leading-snug">{l.title}</span>
                        <span className="block text-[10px] uppercase tracking-wider text-[color:var(--text-muted)] mt-1">
                          {l.duration_minutes}m
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>
        </aside>
      </div>
    </div>
  );
}
