import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger,} from '../components/ui/accordion';
import { coursesAPI, lessonsAPI, enrollmentsAPI, settingsAPI, } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import {Clock, BookOpen, CheckCircle, Play, ArrowLeft, Lock, CreditCard, Users, Star, Award, GraduationCap, Briefcase, Quote, Sparkles,Target,ShieldCheck,Rocket,HeartHandshake,Lightbulb,MessageCircle,X,TrendingUp,Gift,ListChecks,Minus,} from 'lucide-react';

/* ----------------------------- Static fallbacks ---------------------------- */

const STATIC_INSTRUCTOR = {
  name: 'Dr. Adaeze Okafor',
  photo:
    'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600&q=80&auto=format&fit=crop',
  qualifications: 'PhD in Computer Science, M.Sc. Software Engineering',
  experience: '12+ years of industry & teaching experience',
  bio: 'Adaeze has led engineering teams at multinational tech firms and trained over 5,000 students across Africa. She combines real-world product experience with a passion for mentorship to help learners ship work that gets them hired.',
};

// Map allowed string icon names (from settings) to lucide-react components.
const ICON_MAP = {
  Rocket,
  HeartHandshake,
  ShieldCheck,
  Lightbulb,
  Sparkles,
  Target,
  Award,
  GraduationCap,
};
const resolveIcon = (icon, fallback) => {
  if (!icon) return fallback;
  if (typeof icon === 'string') return ICON_MAP[icon] || fallback;
  return icon;
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

const CAREERS = [
  { role: 'Data Analyst', salary: '₦300,000 – ₦1.2M/month' },
  { role: 'Business Analyst', salary: '₦400,000 – ₦1.5M/month' },
  { role: 'Power BI Developer', salary: '₦500,000 – ₦2M/month' },
  { role: 'Data Scientist', salary: '₦700,000 – ₦3M/month' },
];

const PROBLEMS = [
  'Struggling to get a tech job despite applying everywhere',
  'Watching endless tutorials without any practical results',
  'Learning randomly without a clear, structured roadmap',
  'Unsure which skills employers actually want to see',
];

const OFFER_INCLUDES = [
  'Full lifetime course access',
  'Verifiable certificate of completion',
  'Hands-on portfolio projects',
  '1:1 mentor support & code reviews',
  'All future curriculum updates',
  'Private student community access',
  'Bonus resources & cheatsheets',
];

/* ToC sections — id must match the <section id="..."> attribute below */
const SECTIONS = [
  { id: 'hero', label: 'Overview' },
  { id: 'problems', label: 'The Challenge' },
  { id: 'outcomes', label: "What You'll Learn" },
  { id: 'curriculum', label: 'Curriculum' },
  { id: 'projects', label: 'Projects' },
  { id: 'careers', label: 'Careers' },
  { id: 'instructor', label: 'Instructor' },
  { id: 'testimonials', label: 'Reviews' },
  { id: 'compare', label: 'Compare' },
  { id: 'offer', label: 'Pricing' },
  { id: 'guarantee', label: 'Guarantee' },
  { id: 'faq', label: 'FAQ' },
];

/* Comparison table — Orbal Academy vs. Self-Taught vs. Traditional Bootcamp */
const COMPARE_COLUMNS = [
  { key: 'orbal', label: 'Orbal Academy', highlight: true },
  { key: 'self', label: 'Self-Taught' },
  { key: 'bootcamp', label: 'Traditional Bootcamp' },
];

const COMPARE_ROWS = [
  {
    feature: 'Structured, job-focused roadmap',
    orbal: true,
    self: false,
    bootcamp: true,
  },
  {
    feature: 'Hands-on portfolio projects',
    orbal: true,
    self: 'partial',
    bootcamp: true,
  },
  {
    feature: '1:1 mentor support & code reviews',
    orbal: true,
    self: false,
    bootcamp: 'partial',
  },
  {
    feature: 'Verifiable industry certificate',
    orbal: true,
    self: false,
    bootcamp: true,
  },
  {
    feature: 'Lifetime access & curriculum updates',
    orbal: true,
    self: 'partial',
    bootcamp: false,
  },
  {
    feature: 'Learn at your own pace',
    orbal: true,
    self: true,
    bootcamp: false,
  },
  {
    feature: 'Active peer community',
    orbal: true,
    self: false,
    bootcamp: true,
  },
  {
    feature: 'Time to job-ready',
    orbal: '8–12 weeks',
    self: '6+ months',
    bootcamp: '3–6 months',
  },
  {
    feature: 'Typical cost',
    orbal: 'Affordable',
    self: 'Free (but costly in time)',
    bootcamp: '₦1.5M – ₦3M+',
  },
];

/* ----------------------------- Table of Contents --------------------------- */
const TableOfContents = ({ activeId, onJump }) => (
  <nav
    aria-label="Page navigation"
    className="w-full"
  >
  
    <div className="w-full bg-background/80 backdrop-blur-md border border-border rounded-2xl p-4 shadow-lg">
      <div className="flex items-center gap-2 mb-3 px-2">
        <ListChecks className="w-4 h-4 text-primary" />
        <p className="text-xs uppercase tracking-wider font-semibold text-secondary">
          On this page
        </p>
      </div>
      <nav>
        <ul className="space-y-0.5">
          {SECTIONS.map((s) => {
            const isActive = activeId === s.id;
            return (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => onJump(s.id)}
                  className={`group w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-sm transition-colors ${
                    isActive
                      ? 'text-primary font-semibold bg-primary/10'
                      : 'text-muted-foreground hover:text-secondary hover:bg-muted'
                  }`}
                >
                  <span
                    className={`block w-1 h-4 rounded-full transition-all ${
                      isActive
                        ? 'bg-primary'
                        : 'bg-border group-hover:bg-muted-foreground/50'
                    }`}
                  />
                  <span className="truncate">{s.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  </nav>
);

/* ----------------------------- Compare Cell -------------------------------- */

const CompareCell = ({ value, highlight }) => {
  if (value === true) {
    return (
      <span
        className={`inline-flex items-center justify-center w-7 h-7 rounded-full ${
          highlight ? 'bg-primary text-white' : 'bg-green-100 text-green-600'
        }`}
        aria-label="Included"
      >
        <CheckCircle className="w-4 h-4" />
      </span>
    );
  }
  if (value === false) {
    return (
      <span
        className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-red-50 text-red-500"
        aria-label="Not included"
      >
        <X className="w-4 h-4" />
      </span>
    );
  }
  if (value === 'partial') {
    return (
      <span
        className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-amber-50 text-amber-600"
        aria-label="Partial"
      >
        <Minus className="w-4 h-4" />
      </span>
    );
  }
  return (
    <span
      className={`text-sm font-medium ${
        highlight ? 'text-primary' : 'text-secondary'
      }`}
    >
      {value}
    </span>
  );
};

/* ----------------------------- Section heading ----------------------------- */

const SectionHeading = ({ eyebrow, title, subtitle, align = 'left', light = false }) => (
  <div className={`mb-10 ${align === 'center' ? 'text-center max-w-2xl mx-auto' : ''}`}>
    {eyebrow && (
      <p className="text-primary font-medium uppercase tracking-wider text-xs mb-3">
        {eyebrow}
      </p>
    )}
    <h2
      className={`font-serif text-3xl md:text-4xl font-bold mb-3 ${
        light ? 'text-white' : 'text-secondary'
      }`}
    >
      {title}
    </h2>
    {subtitle && (
      <p
        className={`text-base md:text-lg ${
          light ? 'text-white/70' : 'text-muted-foreground'
        }`}
      >
        {subtitle}
      </p>
    )}
  </div>
);

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
  const [showStickyBar, setShowStickyBar] = useState(false);
  const [activeSection, setActiveSection] = useState('hero');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [courseRes, lessonsRes] = await Promise.all([
          coursesAPI.getOne(id),
          lessonsAPI.getByCourse(id),
        ]);
        setCourse(courseRes.data);
        setLessons(lessonsRes.data);

        if (settingsAPI?.get) {
          try {
            const settingsRes = await settingsAPI.get();
            if (settingsRes?.data?.why_choose_items?.length) {
              setWhyChoose(settingsRes.data.why_choose_items);
            }
          } catch (err) {
            // silently fall back
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

  // Show sticky CTA bar after user scrolls past the hero
  useEffect(() => {
    const onScroll = () => setShowStickyBar(window.scrollY > 600);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Scroll-spy: track which section is currently in view
  useEffect(() => {
    if (loading) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) {
          setActiveSection(visible[0].target.id);
        }
      },
      {
        rootMargin: '-30% 0px -60% 0px',
        threshold: 0,
      }
    );
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [loading]);

  const handleJump = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

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
          image:
            'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800&q=80&auto=format&fit=crop',
        },
        {
          title: 'Industry-style Case Study',
          description:
            'Tackle a realistic brief modeled on actual hiring tests used by top tech companies.',
          image:
            'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&q=80&auto=format&fit=crop',
        },
        {
          title: 'Collaborative Mini-Build',
          description:
            'Practice working with version control and code review in a small team-style sprint.',
          image:
            'https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800&q=80&auto=format&fit=crop',
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
  const careers = course.careers?.length ? course.careers : CAREERS;

  /* NEW: per-course fallback resolution for previously-static sections.
     Priority: course.X → (settings for why_choose) → STATIC_X */
  const problems = course.problems?.length ? course.problems : PROBLEMS;
  const offerIncludes = course.offer_includes?.length
    ? course.offer_includes
    : OFFER_INCLUDES;
  const compareRows = course.compare_rows?.length
    ? course.compare_rows
    : COMPARE_ROWS;
  const whyItems =
    (course.why_choose?.length ? course.why_choose : whyChoose) ||
    STATIC_WHY_CHOOSE;


  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
  
      <div className="flex-1">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
  
          <div className="xl:flex gap-10">
    
            {/* Sidebar */}
            <aside className="hidden xl:block w-40 shrink-0">
                <div className="fixed top-24 w-40">
                    <div className="rounded-xl border border-border/50 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 p-2">
                        <TableOfContents
                            activeId={activeSection}
                            onJump={handleJump}
                        />
                    </div>
                </div>
            </aside>
            
            {/* Main Content */}
            <main className="flex-1 min-w-0">

      {/* 1. HERO */}
      <section
        id="hero"
        className="relative overflow-hidden bg-secondary py-16 md:py-24 lg:py-28"
        data-testid="hero-section"
      >
        {/* Background image */}
        <div className="absolute inset-0">
          <img
            src={
              course.image_url ||
              "https://images.unsplash.com/photo-1665586510291-ae722d1d1f00?crop=entropy&cs=srgb&fm=jpg&q=85"
            }
            alt=""
            aria-hidden="true"
            className="h-full w-full object-cover"
            data-testid="hero-course-image"
          />
          {/* Dark overlays for text legibility */}
          <div className="absolute inset-0 bg-secondary/85" />
          <div className="absolute inset-0 bg-gradient-to-r from-secondary via-secondary/85 to-secondary/60" />
          {/* Ambient accents */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.08),transparent_45%)]" />
          <div className="absolute -left-20 bottom-0 h-72 w-72 rounded-full bg-primary/15 blur-[120px]" />
          <div className="absolute -right-24 top-0 h-96 w-96 rounded-full bg-primary/10 blur-[160px]" />
        </div>
      
        <div className="container relative">
          {/* Back Button */}
          <Link
            to="/courses"
            className="mb-10 inline-flex items-center gap-2 text-white/70 transition-colors hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Courses
          </Link>
      
          <div className="max-w-3xl">
            <p className="mb-4 text-sm font-semibold uppercase tracking-[0.25em] text-primary">
              Professional Training Program
            </p>
      
            <div className="mb-6 flex flex-wrap gap-3">
              <Badge className="border border-primary/30 bg-primary/15 text-primary backdrop-blur-sm">
                Practical-Oriented
              </Badge>
      
              <Badge className="border border-white/10 bg-white/10 text-white">
                Career-Focused
              </Badge>
      
              <Badge className="border border-white/10 bg-white/10 text-white">
                Professional Certificate
              </Badge>
            </div>
      
            <h1 className="font-serif text-5xl font-bold leading-[1.05] tracking-tight text-white md:text-6xl xl:text-7xl">
              {course.title}
            </h1>
      
            <p className="mt-6 max-w-2xl text-lg leading-8 text-white/75">
              {course.short_description}
            </p>
      
            {/* Course Stats */}
            <div className="mt-10 flex flex-wrap gap-4">
              <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 backdrop-blur">
                <Clock className="h-4 w-4 text-primary" />
                <span className="text-sm text-white/80">{course.duration}</span>
              </div>
      
              <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 backdrop-blur">
                <BookOpen className="h-4 w-4 text-primary" />
                <span className="text-sm text-white/80">
                  {lessons.length} Lessons
                </span>
              </div>
      
              <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 backdrop-blur">
                <Star className="h-4 w-4 fill-primary text-primary" />
                <span className="text-sm text-white/80">
                  4.9 (5,200+ Students)
                </span>
              </div>
            </div>
      
            {/* Pricing Card */}
            <div className="mt-12 rounded-3xl border border-white/10 bg-white/5 p-8 shadow-2xl backdrop-blur-xl transition-all hover:border-primary/30">
              <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.2em] text-white/50">
                    Course Price
                  </p>
      
                  <p className="mt-2 text-4xl font-bold leading-none text-primary md:text-5xl">
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
      
              <div className="mt-8 grid gap-4 border-t border-white/10 pt-6 sm:grid-cols-2">
                {[
                  "Beginner friendly",
                  "Hands-on projects",
                  "Professional certificate",
                  "Lifetime access",
                ].map((item) => (
                  <div key={item} className="flex items-start gap-3">
                    <CheckCircle className="mt-0.5 h-5 w-5 text-primary" />
                    <span className="text-sm text-white/80">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
  
      {/* 2. TRUST BAR */}
      <section className="bg-background border-y border-border" data-testid="trust-bar">
        <div>
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

      {/* 3. PROBLEM/AGITATE */}
      <section id="problems" className="py-16 md:py-20 bg-muted/30">
        <div>
          <SectionHeading
            eyebrow="Common Challenges"
            title="Are you facing any of these problems?"
            subtitle="If you nodded to any of these, you're in the right place."
            align="center"
          />
          <div className="grid sm:grid-cols-2 gap-4 max-w-4xl mx-auto">
            {problems.map((item, index) => (
              <Card key={index} className="border-border/60">
                <CardContent className="p-5 flex items-start gap-3">
                  <span className="w-7 h-7 rounded-full bg-red-100 text-red-600 flex items-center justify-center flex-shrink-0">
                    <X className="w-4 h-4" />
                  </span>
                  <p className="text-secondary">{item}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 4. WHAT YOU'LL LEARN */}
      {course.learning_outcomes?.length > 0 && (
        <section id="outcomes" className="py-16 md:py-20 bg-background" data-testid="learning-outcomes-section">
          <div>
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

      {/* 5. CURRICULUM */}
      <section id="curriculum" className="py-16 md:py-20 bg-muted/30" data-testid="curriculum-section">
        <div>
          <SectionHeading
            eyebrow="Curriculum"
            title="What's inside the course"
            subtitle={`${lessons.length} hands-on lessons designed to build skills progressively.`}
          />
          {lessons.length > 0 ? (
            <div className="space-y-3 mb-10 max-w-3xl mx-auto">
              {lessons.map((lesson, index) => (
                <Card key={lesson.id} className="border-border/60 hover:border-primary/40 transition-colors">
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

      {/* 6. PROJECTS YOU'LL BUILD */}
      <section id="projects" className="py-16 md:py-20 bg-background">
        <div>
          <SectionHeading
            eyebrow="Portfolio Projects"
            title="Projects you'll build"
            subtitle="Real-world projects designed to impress hiring managers."
            align="center"
          />
          <div className="grid md:grid-cols-3 gap-6">
            {projects.map((project, index) => (
              <Card key={index} className="overflow-hidden hover:shadow-lg transition-shadow">
                <img
                  src={
                    project.image ||
                    'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800&q=80&auto=format&fit=crop'
                  }
                  alt={project.title}
                  className="w-full aspect-video object-cover"
                />
                <CardContent className="p-6">
                  <h3 className="font-serif text-xl font-bold text-secondary mb-2">
                    {project.title}
                  </h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {project.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 7. CAREER OPPORTUNITIES */}
      <section id="careers" className="py-16 md:py-20 bg-muted/30">
        <div>
          <SectionHeading
            eyebrow="Career Opportunities"
            title="Where this course can take you"
            subtitle="Roles our graduates land — with real salary ranges."
            align="center"
          />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {careers.map((career, i) => (
              <Card
                key={i}
                className="border-border/60 hover:border-primary/40 transition-colors group"
              >
                <CardContent className="p-6">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                    <Briefcase className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="font-serif text-lg font-bold text-secondary mb-2">
                    {career.role}
                  </h3>
                  <div className="flex items-center gap-1.5 text-primary font-semibold">
                    <TrendingUp className="w-4 h-4" />
                    <span>{career.salary}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 8. MEET YOUR INSTRUCTOR */}
      <section id="instructor" className="py-16 md:py-20 bg-background" data-testid="instructor-section">
        <div>
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

      {/* 9. TESTIMONIALS */}
      <section id="testimonials" className="py-16 md:py-20 bg-muted/30" data-testid="testimonials-section">
        <div>
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
                  <p className="text-secondary mb-5 flex-1 leading-relaxed">
                    &ldquo;{t.quote}&rdquo;
                  </p>
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

      {/* 10. WHO THIS COURSE IS FOR */}
      <section className="py-16 md:py-20 bg-background" data-testid="who-for-section">
        <div>
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
                  className="flex items-start gap-3 bg-muted/40 rounded-xl p-4 border border-border/60"
                >
                  <Target className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                  <span className="text-secondary">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* 11. REQUIREMENTS */}
      <section className="py-16 md:py-20 bg-muted/30" data-testid="requirements-section">
        <div>
          <SectionHeading
            eyebrow="Requirements"
            title="What you need to get started"
            align="center"
          />
          <ul className="space-y-3">
            {requirements.map((req, i) => (
              <li
                key={i}
                className="flex items-start gap-3 bg-background rounded-xl p-4 border border-border/60"
              >
                <CheckCircle className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <span className="text-secondary">{req}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* 12. WHY CHOOSE ORBAL ACADEMY */}
      <section className="py-16 md:py-20 bg-secondary" data-testid="why-choose-section">
        <div>
          <SectionHeading
            eyebrow="Why choose us"
            title="Why choose Orbal Academy?"
            subtitle="We're built around outcomes — your portfolio, your skills, your career."
            align="center"
            light
          />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {whyItems.map((item, i) => {
              const fallbackIcon =
                STATIC_WHY_CHOOSE[i % STATIC_WHY_CHOOSE.length].icon;
              const Icon = resolveIcon(item.icon, fallbackIcon);
              return (
                <div
                  key={i}
                  className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10 hover:border-primary/40 transition-colors"
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

      {/* 13. COMPARISON TABLE */}
      <section id="compare" className="py-16 md:py-20 bg-background">
        <div>
          <SectionHeading
            eyebrow="The Smart Choice"
            title="Orbal Academy vs. The Alternatives"
            subtitle="See exactly how we compare to learning alone or paying for a traditional bootcamp."
            align="center"
          />

          {/* Desktop table */}
          <div className="hidden md:block">
            <div className="overflow-hidden rounded-2xl border border-border shadow-sm">
              <table className="w-full">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="text-left p-5 font-medium text-secondary text-sm uppercase tracking-wider w-2/5">
                      Feature
                    </th>
                    {COMPARE_COLUMNS.map((col) => (
                      <th
                        key={col.key}
                        className={`p-5 text-center text-sm uppercase tracking-wider font-semibold ${
                          col.highlight
                            ? 'text-primary bg-primary/5'
                            : 'text-muted-foreground'
                        }`}
                      >
                        {col.highlight && (
                          <div className="flex justify-center mb-1">
                            <span className="inline-flex items-center gap-1 text-[10px] bg-primary text-white px-2 py-0.5 rounded-full normal-case tracking-wide">
                              <Sparkles className="w-3 h-3" />
                              Recommended
                            </span>
                          </div>
                        )}
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {compareRows.map((row, i) => (
                    <tr
                      key={i}
                      className={`border-t border-border ${
                        i % 2 === 1 ? 'bg-muted/20' : ''
                      }`}
                    >
                      <td className="p-5 text-secondary font-medium">
                        {row.feature}
                      </td>
                      {COMPARE_COLUMNS.map((col) => (
                        <td
                          key={col.key}
                          className={`p-5 text-center ${
                            col.highlight ? 'bg-primary/5' : ''
                          }`}
                        >
                          <CompareCell
                            value={row[col.key]}
                            highlight={col.highlight}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile card-stack view */}
          <div className="md:hidden space-y-6">
            {COMPARE_COLUMNS.map((col) => (
              <Card
                key={col.key}
                className={
                  col.highlight
                    ? 'border-primary/40 shadow-md ring-1 ring-primary/20'
                    : 'border-border/60'
                }
              >
                <CardContent className="p-5">
                  <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
                    <h3
                      className={`font-serif text-lg font-bold ${
                        col.highlight ? 'text-primary' : 'text-secondary'
                      }`}
                    >
                      {col.label}
                    </h3>
                    {col.highlight && (
                      <span className="inline-flex items-center gap-1 text-[10px] bg-primary text-white px-2 py-1 rounded-full uppercase tracking-wide">
                        <Sparkles className="w-3 h-3" />
                        Best
                      </span>
                    )}
                  </div>
                  <ul className="space-y-3">
                    {compareRows.map((row, i) => (
                      <li
                        key={i}
                        className="flex items-center justify-between gap-3"
                      >
                        <span className="text-sm text-secondary flex-1">
                          {row.feature}
                        </span>
                        <CompareCell
                          value={row[col.key]}
                          highlight={col.highlight}
                        />
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="flex justify-center mt-10">
            <EnrollCTA
              hasAccess={hasAccess}
              enrollment={enrollment}
              course={course}
              onEnroll={handleEnrollClick}
              variant="compare"
            />
          </div>
        </div>
      </section>

      {/* 14. OFFER STACK / INVESTMENT */}
      <section id="offer" className="py-16 md:py-24 bg-primary/5">
        <div>
          <SectionHeading
            eyebrow="Investment"
            title="Everything you need to succeed"
            subtitle="One enrollment. Full access. No hidden fees."
            align="center"
          />
          <Card className="border-primary/30 shadow-xl">
            <CardContent className="p-8 md:p-10">
              <div className="flex items-center gap-2 mb-6">
                <Gift className="w-6 h-6 text-primary" />
                <p className="font-semibold text-secondary">What&apos;s included:</p>
              </div>
              <ul className="space-y-3 mb-8">
                {offerIncludes.map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <CheckCircle className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                    <span className="text-secondary">{item}</span>
                  </li>
                ))}
              </ul>

              <div className="border-t border-border pt-6 text-center">
                <p className="text-muted-foreground line-through text-sm mb-1">
                  Total value: ₦450,000
                </p>
                <p className="text-xs uppercase tracking-wider text-primary font-medium mb-1">
                  Your price today
                </p>
                <p className="text-4xl md:text-5xl font-bold text-primary mb-6">
                  {formatPrice(course.price)}
                </p>
                <EnrollCTA
                  hasAccess={hasAccess}
                  enrollment={enrollment}
                  course={course}
                  onEnroll={handleEnrollClick}
                  variant="offer"
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* 15. MONEY-BACK GUARANTEE */}
      <section id="guarantee" className="py-16 bg-background">
        <div>
          <Card className="border-primary/30 bg-primary/5">
            <CardContent className="p-8 md:p-10 text-center">
              <div className="w-20 h-20 rounded-full bg-primary/15 flex items-center justify-center mx-auto mb-5">
                <ShieldCheck className="w-10 h-10 text-primary" />
              </div>
              <h2 className="font-serif text-2xl md:text-3xl font-bold text-secondary mb-3">
                7-Day Money-Back Guarantee
              </h2>
              <p className="text-muted-foreground leading-relaxed max-w-xl mx-auto">
                Try the course risk-free. If you&apos;re not satisfied within the first
                7 days, we&apos;ll refund your payment — no questions asked.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* 16. FAQ */}
      <section id="faq" className="py-16 md:py-20 bg-muted/30" data-testid="faq-section">
        <div>
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
          </main>

        </div>
      </div>
    </div>

      <Footer />

      {/* MOBILE STICKY CTA BAR */}
      {!hasAccess && !enrollment && showStickyBar && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-background border-t border-border md:hidden shadow-[0_-4px_20px_rgba(0,0,0,0.08)]">
          <div className="flex justify-between items-center p-3 px-4">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                Course Price
              </p>
              <p className="font-bold text-secondary text-lg leading-none">
                {formatPrice(course.price)}
              </p>
            </div>
            <Button
              onClick={handleEnrollClick}
              className="rounded-full px-6"
              data-testid="enroll-now-btn-sticky"
            >
              <CreditCard className="w-4 h-4 mr-2" />
              Enroll Now
            </Button>
          </div>
        </div>
      )}

      {/* WHATSAPP FLOATING BUTTON */}
      <a
        href="https://wa.me/2348127319882"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Chat with us on WhatsApp"
        className="fixed bottom-24 right-5 md:bottom-6 z-50 bg-green-500 hover:bg-green-600 text-white p-3.5 rounded-full shadow-lg hover:shadow-xl transition-all hover:scale-105 flex items-center justify-center"
      >
        <MessageCircle className="w-6 h-6" />
        <span className="sr-only">WhatsApp</span>
      </a>
    </div>
  );
};

export default CourseDetailPage;
