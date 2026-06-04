import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import CourseCard from "@/components/CourseCard";
import { Search } from "lucide-react";

const LEVELS = ["all", "beginner", "intermediate", "advanced"];

export default function CoursesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [courses, setCourses] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  const q = searchParams.get("q") || "";
  const category = searchParams.get("category") || "all";
  const level = searchParams.get("level") || "all";

  useEffect(() => {
    api.get("/courses/categories").then((r) => setCategories(r.data));
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (q) params.q = q;
    if (category !== "all") params.category = category;
    if (level !== "all") params.level = level;
    api
      .get("/courses", { params })
      .then((r) => setCourses(r.data))
      .finally(() => setLoading(false));
  }, [q, category, level]);

  const setParam = (k, v) => {
    const next = new URLSearchParams(searchParams);
    if (!v || v === "all") next.delete(k);
    else next.set(k, v);
    setSearchParams(next);
  };

  return (
    <div data-testid="courses-page" className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-16">
      <div className="mb-12 max-w-3xl fade-up">
        <div className="eyebrow mb-4">Catalog</div>
        <h1 className="font-display text-5xl sm:text-6xl tracking-tighter leading-none mb-5">
          Every course we offer.
        </h1>
        <p className="text-[color:var(--text-muted)] text-base md:text-lg leading-relaxed">
          Filter by discipline or skill level. New cohorts open seasonally — paid courses include lifetime access.
        </p>
      </div>

      {/* filters */}
      <div className="border-y border-black/10 py-6 mb-12 grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
        <div className="md:col-span-5 flex items-center gap-3 border-b border-[color:var(--border)] focus-within:border-[color:var(--accent)] pb-2">
          <Search className="w-4 h-4 text-[color:var(--text-muted)]" strokeWidth={1.5} />
          <input
            data-testid="courses-search-input"
            type="search"
            placeholder="Search courses, tags, topics…"
            value={q}
            onChange={(e) => setParam("q", e.target.value)}
            className="flex-1 bg-transparent outline-none text-sm py-1"
          />
        </div>
        <div className="md:col-span-4 flex items-center gap-2 flex-wrap">
          <span className="eyebrow mr-2">Category</span>
          <button
            data-testid="filter-cat-all"
            onClick={() => setParam("category", "all")}
            className={`text-xs uppercase tracking-wider px-3 py-1.5 border ${category === "all" ? "border-[color:var(--accent)] text-[color:var(--accent)]" : "border-black/15 text-[color:var(--text-muted)]"}`}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              data-testid={`filter-cat-${c}`}
              key={c}
              onClick={() => setParam("category", c)}
              className={`text-xs uppercase tracking-wider px-3 py-1.5 border ${category === c ? "border-[color:var(--accent)] text-[color:var(--accent)]" : "border-black/15 text-[color:var(--text-muted)]"}`}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="md:col-span-3 flex items-center gap-2 flex-wrap md:justify-end">
          <span className="eyebrow mr-2">Level</span>
          {LEVELS.map((l) => (
            <button
              data-testid={`filter-level-${l}`}
              key={l}
              onClick={() => setParam("level", l)}
              className={`text-xs uppercase tracking-wider px-3 py-1.5 border ${level === l ? "border-[color:var(--accent)] text-[color:var(--accent)]" : "border-black/15 text-[color:var(--text-muted)]"}`}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center eyebrow">Loading catalog…</div>
      ) : courses.length === 0 ? (
        <div className="py-20 text-center text-[color:var(--text-muted)]">
          No courses match your filters.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
          {courses.map((c, i) => (
            <CourseCard course={c} index={i} key={c.id} />
          ))}
        </div>
      )}
    </div>
  );
}
