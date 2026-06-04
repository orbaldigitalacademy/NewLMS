import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import CourseCard from "@/components/CourseCard";
import { ArrowRight, Sparkles, Quote } from "lucide-react";

const HERO_IMAGE =
  "https://images.unsplash.com/photo-1512486130939-2c4f79935e4f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NjV8MHwxfHNlYXJjaHwzfHxtaW5pbWFsaXN0JTIwd29ya3NwYWNlJTIwbGFwdG9wJTIwY29mZmVlfGVufDB8fHx8MTc4MDU5Mzc4M3ww&ixlib=rb-4.1.0&q=85";

export default function HomePage() {
  const [courses, setCourses] = useState([]);
  const [testimonials, setTestimonials] = useState([]);

  useEffect(() => {
    (async () => {
      const [c, t] = await Promise.all([
        api.get("/courses").catch(() => ({ data: [] })),
        api.get("/testimonials", { params: { featured_only: true } }).catch(() => ({ data: [] })),
      ]);
      setCourses(c.data.slice(0, 4));
      setTestimonials(t.data.slice(0, 3));
    })();
  }, []);

  return (
    <div data-testid="home-page">
      {/* HERO - editorial Tetris grid */}
      <section className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 pt-12 md:pt-20 pb-24 grid grid-cols-1 md:grid-cols-12 gap-8 md:gap-12">
        <div className="md:col-span-7 fade-up">
          <div className="eyebrow mb-6">
            <span className="text-[color:var(--accent)]">Vol. 04 ·</span> Spring Studio Term
          </div>
          <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl tracking-tighter leading-[0.95] mb-8">
            Learning,<br />
            <span className="italic text-[color:var(--accent)]">unhurried.</span><br />
            Built for craft.
          </h1>
          <p className="text-base md:text-lg leading-relaxed text-[color:var(--text-muted)] max-w-xl mb-10">
            A small, opinionated studio offering long-form courses in design,
            engineering, product, and writing. No certificates farms, no autoplay
            tricks—just deliberate practice with instructors who ship.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <Link to="/courses" data-testid="hero-cta-courses" className="btn-primary">
              Browse Catalog <ArrowRight className="w-4 h-4" strokeWidth={1.5} />
            </Link>
            <Link to="/register" data-testid="hero-cta-register" className="btn-ghost">
              Apply to study
            </Link>
          </div>
          <div className="mt-14 flex items-center gap-10">
            <div>
              <div className="font-display text-4xl text-[color:var(--accent)]">12</div>
              <div className="eyebrow mt-1">Studios</div>
            </div>
            <div>
              <div className="font-display text-4xl">2,400+</div>
              <div className="eyebrow mt-1">Alumni</div>
            </div>
            <div>
              <div className="font-display text-4xl">4.9</div>
              <div className="eyebrow mt-1">Avg Rating</div>
            </div>
          </div>
        </div>

        <div className="md:col-span-5 fade-up fade-up-2">
          <div className="relative">
            <img
              src={HERO_IMAGE}
              alt="A focused workspace"
              className="w-full h-[460px] md:h-[560px] object-cover noise-overlay"
            />
            <div className="absolute -bottom-6 -left-6 hidden md:block bg-[var(--bg)] px-6 py-5 border border-black/10 max-w-[260px]">
              <Sparkles className="w-5 h-5 text-[color:var(--accent)] mb-3" strokeWidth={1.5} />
              <p className="text-sm leading-snug">
                <em className="font-display text-lg">Spring 26 cohort.</em> Applications close March 15.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* MARQUEE-ish line */}
      <div className="border-y border-black/10 bg-white">
        <div className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-4 flex items-center justify-between flex-wrap gap-3 text-xs font-mono uppercase tracking-[0.2em] text-[color:var(--text-muted)]">
          <span>Design</span>
          <span>•</span>
          <span>Engineering</span>
          <span>•</span>
          <span>Product</span>
          <span>•</span>
          <span>Writing</span>
          <span>•</span>
          <span>Lifetime access</span>
          <span>•</span>
          <span>Certificates on completion</span>
        </div>
      </div>

      {/* FEATURED COURSES */}
      <section className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-24">
        <div className="flex items-end justify-between mb-12 gap-6 flex-wrap">
          <div className="max-w-xl">
            <div className="eyebrow mb-4">Catalog · Featured</div>
            <h2 className="font-display text-4xl sm:text-5xl tracking-tight leading-none">
              Courses, like books — designed to be returned to.
            </h2>
          </div>
          <Link to="/courses" data-testid="featured-view-all" className="editorial-link text-sm whitespace-nowrap">
            View entire catalog →
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8">
          {courses.map((c, i) => (
            <CourseCard course={c} index={i} key={c.id} />
          ))}
        </div>
      </section>

      {/* MANIFESTO */}
      <section className="bg-[#1C1917] text-white py-24 noise-overlay">
        <div className="max-w-[1100px] mx-auto px-6 md:px-10 lg:px-16">
          <div className="eyebrow text-white/60 mb-8">Manifesto</div>
          <p className="font-display text-3xl sm:text-4xl lg:text-5xl leading-tight">
            We believe in <em className="text-[color:var(--accent-2)]">slow</em> education.
            In assignments that take a week, not an hour. In feedback from people
            who actually <span className="underline decoration-[color:var(--accent-2)] decoration-2 underline-offset-8">make</span> things.
            And in the kind of skill that lasts a career.
          </p>
        </div>
      </section>

      {/* TESTIMONIALS */}
      {testimonials.length > 0 && (
        <section className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-24">
          <div className="eyebrow mb-4">Voices · Alumni</div>
          <h2 className="font-display text-4xl sm:text-5xl tracking-tight leading-none mb-12 max-w-2xl">
            From students who finished the work.
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
            {testimonials.map((t, i) => (
              <article
                key={t.id}
                data-testid={`testimonial-${t.id}`}
                className={`surface-card p-8 fade-up fade-up-${(i % 5) + 1}`}
              >
                <Quote className="w-7 h-7 text-[color:var(--accent)] mb-5" strokeWidth={1.5} />
                <p className="text-base leading-relaxed mb-7">"{t.quote}"</p>
                <div className="flex items-center gap-3 border-t border-black/10 pt-5">
                  {t.avatar_url ? (
                    <img
                      src={t.avatar_url}
                      alt={t.name}
                      className="w-10 h-10 object-cover"
                    />
                  ) : (
                    <div className="w-10 h-10 bg-[color:var(--accent)] text-white flex items-center justify-center font-display text-lg">
                      {t.name.charAt(0)}
                    </div>
                  )}
                  <div>
                    <div className="font-semibold text-sm">{t.name}</div>
                    <div className="text-xs text-[color:var(--text-muted)]">{t.role}</div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* CONTACT CTA */}
      <section className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 pb-24">
        <div className="border border-black/10 bg-white p-10 md:p-16 grid grid-cols-1 md:grid-cols-12 gap-8 items-center">
          <div className="md:col-span-8">
            <div className="eyebrow mb-4">A note</div>
            <h2 className="font-display text-3xl sm:text-4xl leading-tight mb-3">
              Have a question, a custom cohort, or a partnership in mind?
            </h2>
            <p className="text-[color:var(--text-muted)]">
              We read every message. Get in touch and we'll respond within two business days.
            </p>
          </div>
          <div className="md:col-span-4 md:text-right">
            <Link to="/contact" data-testid="contact-cta" className="btn-primary">
              Start a conversation <ArrowRight className="w-4 h-4" strokeWidth={1.5} />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
