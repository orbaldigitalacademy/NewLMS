import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '../components/ui/accordion';
import { coursesAPI, lessonsAPI, enrollmentsAPI, settingsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import {
  Clock,
  BookOpen,
  CheckCircle,
  Play,
  ArrowLeft,
  Lock,
  CreditCard,
  Users,
  Star,
  Award,
  GraduationCap,
  Briefcase,
  Quote,
  Sparkles,
  Target,
  ShieldCheck,
  Rocket,
  HeartHandshake,
  Lightbulb,
} from 'lucide-react';

/* ----------------------------- Static fallbacks ---------------------------- */

const STATIC_INSTRUCTOR = {
  name: 'Dr. Adaeze Okafor',
  photo:
    'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600&q=80&auto=format&fit=crop',
  qualifications: 'PhD in Computer Science, M.Sc. Software Engineering',
  experience: '12+ years of industry & teaching experience',
  bio: 'Adaeze has led engineering teams at multinational tech firms and trained over 5,000 students across Africa. She combines real-world product experience with a passion for mentorship to help learners ship work that gets them hired.',
};

const STATIC_WHY_CHOOSE = [
  {
    icon: Rocket,
    title: 'Project-first learning',
    description: 'Every module ends with a real, portfolio-worthy build — not just theory.',
  },
  {
    icon: HeartHandshake,
    title: 'Mentor support',
    description: 'Get unstuck fast with direct access to instructors and a peer community.',
  },
  {
    icon: ShieldCheck,
    title: 'Job-ready certificate',
    description: 'Earn a verifiable certificate recognised by hiring partners across Africa.',
  },
  {
    icon: Lightbulb,
    title: 'Lifetime updates',
    description: 'Curriculum stays current — you get every future update at no extra cost.',
  },
];

const TRUST_BAR = [
  { icon: Users, value: '5,200+', label: 'Students enrolled' },
  { icon: Star, value: '4.9 / 5', label: 'Average rating' },
  { icon: CheckCircle, value: '94%', label: 'Completion rate' },
  { icon: Award, value: 'Verified', label: 'Certificate of completion' },
];

/* ----------------------------- Reusable CTA -------------------------------- */

const EnrollCTA = ({ hasAccess, enrollment, course, onEnroll, variant = 'inline' }) => {
  if (hasAccess) {
    return (
      <Link to={`/dashboard/learn/${course.id}`}>
        <Button
          size="lg"
          className="rounded-full px-8 btn-animate"
          data-testid={`start-learning-btn-${variant}`}
        >
          <Play className="w-5 h-5 mr-2" />
          Start Learning
        </Button>
      </Link>
    );
  }
  if (enrollment) {
    return (
      <Badge
        className={`text-sm px-4 py-2 ${
          enrollment.payment_status === 'pending'
            ? 'badge-pending'
            : enrollment.payment_status === 'rejected'
            ? 'badge-rejected'
            : ''
        }`}
      >
        Payment {enrollment.payment_status}
      </Badge>
    );
  }
  return (
    <Button
      size="lg"
      className="rounded-full px-8 btn-animate"
      onClick={onEnroll}
      data-testid={`enroll-now-btn-${variant}`}
    >
      <CreditCard className="w-5 h-5 mr-2" />
      Enroll Now
    </Button>
  );
};

/* ----------------------------- Section heading ----------------------------- */

const SectionHeading = ({ eyebrow, title, subtitle, align = 'left' }) => (
  <div className={`mb-10 ${align === 'center' ? 'text-center max-w-2xl mx-auto' : ''}`}>
    {eyebrow && (
      <p className="text-primary font-medium uppercase tracking-wider text-xs mb-3">
        {eyebrow}
      </p>
    )}
    <h2 className="font-serif text-3xl md:text-4xl font-bold text-secondary mb-3">
      {title}
    </h2>
    {subtitle && <p className="text-muted-foreground text-base md:text-lg">{subtitle}</p>}
  </div>
);

/* ============================== Main Component ============================ */

const CourseDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [course, setCourse] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);
  const [enrollment, setEnrollment] = useState(null);
  const [whyChoose, setWhyChoose] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [courseRes, lessonsRes] = await Promise.all([
          coursesAPI.getOne(id),
          lessonsAPI.getByCourse(id),
        ]);
        setCourse(courseRes.data);
        setLessons(lessonsRes.data);

        // Optional: site settings for "Why Choose Orbal Academy"
        if (settingsAPI?.get) {
          try {
            const settingsRes = await settingsAPI.get();
            if (settingsRes?.data?.why_choose_items?.length) {
              setWhyChoose(settingsRes.data.why_choose_items);
            }
          } catch (err) {
            // settings optional — silently fall back to static
          }
        }

        if (isAuthenticated) {
          try {
            const accessRes = await enrollmentsAPI.checkAccess(id);
            setHasAccess(accessRes.data.has_access);

            const enrollmentsRes = await enrollmentsAPI.getMy();
            const myEnrollment = enrollmentsRes.data.find((e) => e.course_id === id);
            setEnrollment(myEnrollment);
          } catch (error) {
            console.error('Error checking access:', error);
          }
        }
      } catch (error) {
        console.error('Failed to fetch course:', error);
        toast.error('Course not found');
        navigate('/courses');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id, isAuthenticated, navigate]);

  const formatPrice = (price) =>
    new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0,
    }).format(price);

  const handleEnrollClick = () => {
    if (!isAuthenticated) {
      toast.info('Please login or register to enroll');
      navigate('/login', { state: { from: `/courses/${id}` } });
      return;
    }
    navigate(`/payment/${id}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent" />
        </div>
        <Footer />
      </div>
    );
  }

  if (!course) return null;

  /* Per-course content with safe fallbacks */
  const instructor = course.instructor || STATIC_INSTRUCTOR;
  const testimonials = course.testimonials?.length
    ? course.testimonials
    : [
        {
          name: 'Chinedu A.',
          role: 'Frontend Developer',
          rating: 5,
          quote:
            'The projects were exactly what I needed for my portfolio. I landed a junior role two months after finishing.',
          photo:
            'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?w=200&q=80&auto=format&fit=crop',
        },
        {
          name: 'Funke O.',
          role: 'Product Designer',
          rating: 5,
          quote:
            'Clear, practical and demanding in the right way. The instructor actually answers questions — that made the difference.',
          photo:
            'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&q=80&auto=format&fit=crop',
        },
        {
          name: 'Tunde M.',
          role: 'Career switcher',
          rating: 5,
          quote:
            'I came in with zero background and finished able to build and ship real apps. Worth every naira.',
          photo:
            'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&q=80&auto=format&fit=crop',
        },
      ];
  const projects = course.projects?.length
    ? course.projects
    : [
        {
          title: 'Capstone Portfolio Project',
          description:
            'Plan, build and deploy a production-grade project from scratch — the centerpiece of your portfolio.',
        },
        {
          title: 'Industry-style Case Study',
          description:
            'Tackle a realistic brief modeled on actual hiring tests used by top tech companies.',
        },
        {
          title: 'Collaborative Mini-Build',
          description:
            'Practice working with version control and code review in a small team-style sprint.',
        },
      ];
  const faqs = course.faqs?.length
    ? course.faqs
    : [
        {
          q: 'Do I need prior experience to take this course?',
          a: 'No. The course is structured to take complete beginners to a job-ready level, while still being deep enough for intermediate learners.',
        },
        {
          q: 'How long do I have access to the material?',
          a: 'You get lifetime access — including all future updates to the curriculum.',
        },
        {
          q: 'Will I get a certificate?',
          a: 'Yes. On completion you receive a verifiable certificate of completion you can share on LinkedIn and with employers.',
        },
        {
          q: 'What if the course is not for me?',
          a: 'We offer a 7-day money-back guarantee — no questions asked.',
        },
        {
          q: 'How do I pay?',
          a: 'Click Enroll Now and you’ll be guided through a secure payment flow. We support cards and bank transfer.',
        },
      ];
  const whoFor = course.who_for?.length
    ? course.who_for
    : [
        'Beginners looking to switch into a tech career',
        'Self-taught learners who want structure and accountability',
        'Working professionals upskilling for a promotion or raise',
        'Students preparing for internships and graduate roles',
      ];
  const requirements = course.requirements?.length
    ? course.requirements
    : [
        'A laptop with stable internet access',
        'Willingness to commit ~5 hours per week',
        'No prior coding experience required — we start from fundamentals',
      ];
  const whyItems = whyChoose || STATIC_WHY_CHOOSE;

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* 1. HERO */}
      <section className="bg-secondary py-12 md:py-16" data-testid="hero-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Link
            to="/courses"
            className="inline-flex items-center text-white/70 hover:text-white mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Courses
          </Link>

          <div className="grid lg:grid-cols-2 gap-10 items-center">
            {/* Left column */}
            <div>
              <Badge className="mb-4 bg-primary/15 text-primary hover:bg-primary/15 border-0">
                Premium Course
              </Badge>
              <h1 className="font-serif text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-5 leading-tight">
                {course.title}
              </h1>
              <p className="text-white/80 text-base md:text-lg mb-6 max-w-xl">
                {course.short_description}
              </p>

              <div className="flex flex-wrap gap-5 text-white/70 mb-8">
                <span className="flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  {course.duration}
                </span>
                <span className="flex items-center gap-2">
                  <BookOpen className="w-5 h-5" />
                  {lessons.length} lessons
                </span>
                <span className="flex items-center gap-2">
                  <Star className="w-5 h-5 text-primary fill-primary" />
                  4.9 (5,200+ students)
                </span>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                <div>
                  <p className="text-white/60 text-xs uppercase tracking-wider">
                    Course Price
                  </p>
                  <p className="text-3xl md:text-4xl font-bold text-primary price-tag">
                    {formatPrice(course.price)}
                  </p>
                </div>
                <EnrollCTA
                  hasAccess={hasAccess}
                  enrollment={enrollment}
                  course={course}
                  onEnroll={handleEnrollClick}
                  variant="hero"
                />
              </div>
            </div>

            {/* Right column - image */}
            <div className="relative">
              <div className="absolute -inset-4 bg-primary/20 rounded-3xl blur-2xl" />
              <img
                src={
                  course.image_url ||
                  'https://images.unsplash.com/photo-1665586510291-ae722d1d1f00?crop=entropy&cs=srgb&fm=jpg&q=85'
                }
                alt={course.title}
                className="relative w-full aspect-[4/3] object-cover rounded-2xl shadow-2xl"
                data-testid="hero-course-image"
              />
            </div>
          </div>
        </div>
      </section>

      {/* 2. TRUST BAR */}
      <section className="bg-background border-y border-border" data-testid="trust-bar">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {TRUST_BAR.map((item, i) => {
              const Icon = item.icon;
              return (
                <div
                  key={i}
                  className="flex items-center gap-3"
                  data-testid={`trust-item-${i}`}
                >
                  <div className="w-11 h-11 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-bold text-secondary text-lg leading-none">
                      {item.value}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">{item.label}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 3. WHAT YOU'LL LEARN */}
      {course.learning_outcomes?.length > 0 && (
        <section className="py-16 bg-background" data-testid="learning-outcomes-section">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <SectionHeading
              eyebrow="What you'll learn"
              title="Skills you'll walk away with"
              subtitle="Concrete, employer-recognised outcomes — not vague promises."
            />
            <ul className="grid md:grid-cols-2 gap-4 mb-10">
              {course.learning_outcomes.map((outcome, index) => (
                <li
                  key={index}
                  className="flex items-start gap-3 bg-muted/40 rounded-xl p-4"
                >
                  <CheckCircle className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                  <span className="text-secondary">{outcome}</span>
                </li>
              ))}
            </ul>
            <div className="flex justify-center">
              <EnrollCTA
                hasAccess={hasAccess}
                enrollment={enrollment}
                course={course}
                onEnroll={handleEnrollClick}
                variant="outcomes"
              />
            </div>
          </div>
        </section>
      )}

      {/* 4. CURRICULUM */}
      <section className="py-16 bg-muted/30" data-testid="curriculum-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="Curriculum"
            title="What's inside the course"
            subtitle={`${lessons.length} hands-on lessons designed to build skills progressively.`}
          />
          {lessons.length > 0 ? (
            <div className="space-y-3 mb-10 max-w-3xl mx-auto">
              {lessons.map((lesson, index) => (
                <Card key={lesson.id} className="border-border/60">
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                      {hasAccess ? (
                        <Play className="w-5 h-5 text-primary" />
                      ) : (
                        <Lock className="w-5 h-5 text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-secondary">
                        {String(index + 1).padStart(2, '0')}. {lesson.title}
                      </p>
                      {lesson.description && (
                        <p className="text-sm text-muted-foreground line-clamp-1">
                          {lesson.description}
                        </p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-8">
              Curriculum coming soon
            </p>
          )}
          <div className="flex justify-center">
            <EnrollCTA
              hasAccess={hasAccess}
              enrollment={enrollment}
              course={course}
              onEnroll={handleEnrollClick}
              variant="curriculum"
            />
          </div>
        </div>
      </section>

      {/* 5. MEET YOUR INSTRUCTOR */}
      <section className="py-16 bg-background" data-testid="instructor-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="Meet your instructor"
            title="Learn from someone who's done the work"
          />
          <Card className="overflow-hidden max-w-5xl mx-auto">
            <div className="grid md:grid-cols-[260px_1fr]">
              <div className="relative">
                <img
                  src={instructor.photo}
                  alt={instructor.name}
                  className="w-full h-full object-cover aspect-square md:aspect-auto"
                />
              </div>
              <CardContent className="p-6 md:p-8">
                <h3 className="font-serif text-2xl md:text-3xl font-bold text-secondary mb-1">
                  {instructor.name}
                </h3>
                <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-5 text-sm text-muted-foreground mb-4">
                  <span className="flex items-center gap-2">
                    <GraduationCap className="w-4 h-4 text-primary" />
                    {instructor.qualifications}
                  </span>
                  <span className="flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-primary" />
                    {instructor.experience}
                  </span>
                </div>
                <p className="text-muted-foreground leading-relaxed">{instructor.bio}</p>
              </CardContent>
            </div>
          </Card>
        </div>
      </section>

      {/* 6. TESTIMONIALS */}
      <section className="py-16 bg-muted/30" data-testid="testimonials-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="Student stories"
            title="What our students say"
            subtitle="Real results from people who took the course."
            align="center"
          />
          <div className="grid md:grid-cols-3 gap-6 mb-10">
            {testimonials.map((t, i) => (
              <Card key={i} className="h-full">
                <CardContent className="p-6 flex flex-col h-full">
                  <Quote className="w-7 h-7 text-primary mb-3" />
                  <p className="text-secondary mb-5 flex-1 leading-relaxed">“{t.quote}”</p>
                  <div className="flex items-center gap-3">
                    {t.photo && (
                      <img
                        src={t.photo}
                        alt={t.name}
                        className="w-11 h-11 rounded-full object-cover"
                      />
                    )}
                    <div>
                      <p className="font-semibold text-secondary text-sm">{t.name}</p>
                      <p className="text-xs text-muted-foreground">{t.role}</p>
                    </div>
                    <div className="ml-auto flex gap-0.5">
                      {Array.from({ length: t.rating || 5 }).map((_, idx) => (
                        <Star
                          key={idx}
                          className="w-4 h-4 text-primary fill-primary"
                        />
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="flex justify-center">
            <EnrollCTA
              hasAccess={hasAccess}
              enrollment={enrollment}
              course={course}
              onEnroll={handleEnrollClick}
              variant="testimonials"
            />
          </div>
        </div>
      </section>

      {/* 7. PROJECTS - what students will build */}
      <section className="py-16 bg-background" data-testid="projects-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="Course projects"
            title="What you'll actually build"
            subtitle="Hands-on projects you can showcase to employers from day one."
          />
          <div className="grid md:grid-cols-3 gap-6">
            {projects.map((p, i) => (
              <Card
                key={i}
                className="border-border/60 hover:border-primary/50 transition-colors"
              >
                <CardContent className="p-6">
                  <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                    <Sparkles className="w-5 h-5 text-primary" />
                  </div>
                  <h3 className="font-serif text-lg font-bold text-secondary mb-2">
                    {p.title}
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {p.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 8. WHO THIS COURSE IS FOR */}
      <section className="py-16 bg-muted/30" data-testid="who-for-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-10 items-start max-w-5xl mx-auto">
            <div>
              <SectionHeading
                eyebrow="Who it's for"
                title="Is this course right for you?"
                subtitle="Designed for people who want practical, job-relevant skills — fast."
              />
            </div>
            <ul className="space-y-3">
              {whoFor.map((item, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 bg-background rounded-xl p-4 border border-border/60"
                >
                  <Target className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                  <span className="text-secondary">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* 9. REQUIREMENTS */}
      <section className="py-16 bg-background" data-testid="requirements-section">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="Requirements"
            title="What you need to get started"
            align="center"
          />
          <ul className="space-y-3">
            {requirements.map((req, i) => (
              <li
                key={i}
                className="flex items-start gap-3 bg-muted/40 rounded-xl p-4"
              >
                <CheckCircle className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <span className="text-secondary">{req}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* 10. WHY CHOOSE ORBAL ACADEMY */}
      <section className="py-16 bg-secondary" data-testid="why-choose-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10 max-w-2xl mx-auto">
            <p className="text-primary font-medium uppercase tracking-wider text-xs mb-3">
              Why choose us
            </p>
            <h2 className="font-serif text-3xl md:text-4xl font-bold text-white mb-3">
              Why choose Orbal Academy?
            </h2>
            <p className="text-white/70 text-base md:text-lg">
              We're built around outcomes — your portfolio, your skills, your career.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {whyItems.map((item, i) => {
              const Icon = item.icon || STATIC_WHY_CHOOSE[i % STATIC_WHY_CHOOSE.length].icon;
              return (
                <div
                  key={i}
                  className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10"
                  data-testid={`why-choose-item-${i}`}
                >
                  <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center mb-4">
                    <Icon className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="font-serif text-lg font-bold text-white mb-2">
                    {item.title}
                  </h3>
                  <p className="text-sm text-white/70 leading-relaxed">
                    {item.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 11. FAQ */}
      <section className="py-16 bg-background" data-testid="faq-section">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="FAQ"
            title="Frequently asked questions"
            align="center"
          />
          <Accordion type="single" collapsible className="w-full mb-10">
            {faqs.map((item, i) => (
              <AccordionItem key={i} value={`item-${i}`} data-testid={`faq-item-${i}`}>
                <AccordionTrigger className="text-left font-medium text-secondary">
                  {item.q}
                </AccordionTrigger>
                <AccordionContent className="text-muted-foreground leading-relaxed">
                  {item.a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
          <div className="flex justify-center">
            <EnrollCTA
              hasAccess={hasAccess}
              enrollment={enrollment}
              course={course}
              onEnroll={handleEnrollClick}
              variant="faq"
            />
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default CourseDetailPage;
