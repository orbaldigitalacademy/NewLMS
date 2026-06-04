import { Link } from "react-router-dom";
import { Clock, Layers } from "lucide-react";

export default function CourseCard({ course, index = 0 }) {
  const priceLabel =
    course.price > 0
      ? `₦${course.price.toLocaleString()}`
      : "Free";

  return (
    <Link
      to={`/courses/${course.slug || course.id}`}
      data-testid={`course-card-${course.slug || course.id}`}
      className={`surface-card fade-up fade-up-${(index % 5) + 1} group block`}
    >
      <div className="aspect-[4/3] overflow-hidden bg-[#1c1917]">
        {course.thumbnail_url ? (
          <img
            src={course.thumbnail_url}
            alt={course.title}
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-white font-display text-3xl">
            {course.title?.charAt(0)}
          </div>
        )}
      </div>
      <div className="p-6">
        <div className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-[color:var(--text-muted)] mb-3">
          <span className="font-mono">{course.category}</span>
          <span>{priceLabel}</span>
        </div>
        <h3 className="font-display text-2xl leading-tight mb-2 group-hover:text-[color:var(--accent)] transition-colors">
          {course.title}
        </h3>
        <p className="text-sm text-[color:var(--text-muted)] leading-relaxed line-clamp-2 mb-5">
          {course.short_description}
        </p>
        <div className="flex items-center gap-5 text-xs text-[color:var(--text-muted)]">
          <span className="inline-flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5" strokeWidth={1.5} /> {course.level}
          </span>
          {course.duration_minutes > 0 && (
            <span className="inline-flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" strokeWidth={1.5} />
              {Math.round(course.duration_minutes / 60)} hr
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
