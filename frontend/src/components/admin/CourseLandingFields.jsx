import React from 'react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Plus, Trash2 } from 'lucide-react';

/*
  CourseLandingFields
  -------------------
  Drop-in admin form section for the new course landing-page fields:
    - instructor (object)
    - testimonials[]
    - projects[]
    - faqs[]
    - who_for[]
    - requirements[]

  Usage (inside your existing CourseEditPage / CourseCreatePage):

    const [form, setForm] = useState({
      title: '', short_description: '', ...,
      instructor: { name: '', photo: '', qualifications: '', experience: '', bio: '' },
      testimonials: [],
      projects: [],
      faqs: [],
      who_for: [],
      requirements: [],
    });

    <CourseLandingFields value={form} onChange={setForm} />

  The component mutates only the landing-page fields and leaves the rest of
  your form state untouched.
*/

const emptyInstructor = {
  name: '',
  photo: '',
  qualifications: '',
  experience: '',
  bio: '',
};
const emptyTestimonial = { name: '', role: '', rating: 5, quote: '', photo: '' };
const emptyProject = { title: '', description: '' };
const emptyFaq = { q: '', a: '' };

const SectionTitle = ({ children, hint }) => (
  <div className="mb-3">
    <h3 className="font-semibold text-base text-secondary">{children}</h3>
    {hint && <p className="text-xs text-muted-foreground mt-1">{hint}</p>}
  </div>
);

const CourseLandingFields = ({ value, onChange }) => {
  const v = {
    instructor: value.instructor || { ...emptyInstructor },
    testimonials: value.testimonials || [],
    projects: value.projects || [],
    faqs: value.faqs || [],
    who_for: value.who_for || [],
    requirements: value.requirements || [],
  };

  const patch = (partial) => onChange({ ...value, ...partial });

  /* ---------- Instructor ---------- */
  const setInstructor = (field, val) =>
    patch({ instructor: { ...v.instructor, [field]: val } });

  /* ---------- Array helpers ---------- */
  const addItem = (key, empty) => patch({ [key]: [...v[key], { ...empty }] });
  const removeItem = (key, i) =>
    patch({ [key]: v[key].filter((_, idx) => idx !== i) });
  const updateItem = (key, i, field, val) =>
    patch({
      [key]: v[key].map((item, idx) => (idx === i ? { ...item, [field]: val } : item)),
    });

  /* ---------- Simple string list helpers ---------- */
  const addString = (key) => patch({ [key]: [...v[key], ''] });
  const removeString = (key, i) =>
    patch({ [key]: v[key].filter((_, idx) => idx !== i) });
  const updateString = (key, i, val) =>
    patch({ [key]: v[key].map((s, idx) => (idx === i ? val : s)) });

  return (
    <div className="space-y-8">
      {/* ============================== Instructor ============================ */}
      <Card>
        <CardContent className="p-6 space-y-4">
          <SectionTitle hint="Shown in the 'Meet your instructor' section">
            Instructor
          </SectionTitle>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <Label>Name</Label>
              <Input
                value={v.instructor.name}
                onChange={(e) => setInstructor('name', e.target.value)}
                placeholder="Dr. Adaeze Okafor"
                data-testid="instructor-name-input"
              />
            </div>
            <div>
              <Label>Photo URL</Label>
              <Input
                value={v.instructor.photo}
                onChange={(e) => setInstructor('photo', e.target.value)}
                placeholder="https://..."
                data-testid="instructor-photo-input"
              />
            </div>
            <div>
              <Label>Qualifications</Label>
              <Input
                value={v.instructor.qualifications}
                onChange={(e) => setInstructor('qualifications', e.target.value)}
                placeholder="PhD in Computer Science, M.Sc. Software Eng."
                data-testid="instructor-qualifications-input"
              />
            </div>
            <div>
              <Label>Experience</Label>
              <Input
                value={v.instructor.experience}
                onChange={(e) => setInstructor('experience', e.target.value)}
                placeholder="12+ years industry & teaching"
                data-testid="instructor-experience-input"
              />
            </div>
          </div>
          <div>
            <Label>Short biography</Label>
            <Textarea
              rows={4}
              value={v.instructor.bio}
              onChange={(e) => setInstructor('bio', e.target.value)}
              placeholder="Brief bio shown on the course landing page..."
              data-testid="instructor-bio-input"
            />
          </div>
        </CardContent>
      </Card>

      {/* ============================== Testimonials ========================== */}
      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <SectionTitle hint="Student testimonials displayed on the landing page">
              Testimonials
            </SectionTitle>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => addItem('testimonials', emptyTestimonial)}
              data-testid="add-testimonial-btn"
            >
              <Plus className="w-4 h-4 mr-1" /> Add
            </Button>
          </div>
          {v.testimonials.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No testimonials yet. The frontend will show sensible defaults.
            </p>
          )}
          <div className="space-y-4">
            {v.testimonials.map((t, i) => (
              <div
                key={i}
                className="border border-border rounded-lg p-4 space-y-3"
                data-testid={`testimonial-row-${i}`}
              >
                <div className="grid md:grid-cols-3 gap-3">
                  <div>
                    <Label>Name</Label>
                    <Input
                      value={t.name}
                      onChange={(e) =>
                        updateItem('testimonials', i, 'name', e.target.value)
                      }
                    />
                  </div>
                  <div>
                    <Label>Role</Label>
                    <Input
                      value={t.role || ''}
                      onChange={(e) =>
                        updateItem('testimonials', i, 'role', e.target.value)
                      }
                      placeholder="Frontend Developer"
                    />
                  </div>
                  <div>
                    <Label>Rating (1–5)</Label>
                    <Input
                      type="number"
                      min={1}
                      max={5}
                      value={t.rating ?? 5}
                      onChange={(e) =>
                        updateItem(
                          'testimonials',
                          i,
                          'rating',
                          Math.max(1, Math.min(5, Number(e.target.value) || 5))
                        )
                      }
                    />
                  </div>
                </div>
                <div>
                  <Label>Photo URL</Label>
                  <Input
                    value={t.photo || ''}
                    onChange={(e) =>
                      updateItem('testimonials', i, 'photo', e.target.value)
                    }
                    placeholder="https://..."
                  />
                </div>
                <div>
                  <Label>Quote</Label>
                  <Textarea
                    rows={3}
                    value={t.quote}
                    onChange={(e) =>
                      updateItem('testimonials', i, 'quote', e.target.value)
                    }
                  />
                </div>
                <div className="flex justify-end">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => removeItem('testimonials', i)}
                    data-testid={`remove-testimonial-${i}`}
                  >
                    <Trash2 className="w-4 h-4 mr-1" /> Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ============================== Projects ============================== */}
      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <SectionTitle hint="What students will build">
              Course Projects
            </SectionTitle>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => addItem('projects', emptyProject)}
              data-testid="add-project-btn"
            >
              <Plus className="w-4 h-4 mr-1" /> Add
            </Button>
          </div>
          <div className="space-y-4">
            {v.projects.map((p, i) => (
              <div
                key={i}
                className="border border-border rounded-lg p-4 space-y-3"
                data-testid={`project-row-${i}`}
              >
                <div>
                  <Label>Title</Label>
                  <Input
                    value={p.title}
                    onChange={(e) =>
                      updateItem('projects', i, 'title', e.target.value)
                    }
                    placeholder="Capstone Portfolio Project"
                  />
                </div>
                <div>
                  <Label>Description</Label>
                  <Textarea
                    rows={3}
                    value={p.description}
                    onChange={(e) =>
                      updateItem('projects', i, 'description', e.target.value)
                    }
                  />
                </div>
                <div className="flex justify-end">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => removeItem('projects', i)}
                    data-testid={`remove-project-${i}`}
                  >
                    <Trash2 className="w-4 h-4 mr-1" /> Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ============================== FAQs ================================== */}
      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <SectionTitle hint="Frequently asked questions shown in the FAQ accordion">
              FAQs
            </SectionTitle>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => addItem('faqs', emptyFaq)}
              data-testid="add-faq-btn"
            >
              <Plus className="w-4 h-4 mr-1" /> Add
            </Button>
          </div>
          <div className="space-y-4">
            {v.faqs.map((f, i) => (
              <div
                key={i}
                className="border border-border rounded-lg p-4 space-y-3"
                data-testid={`faq-row-${i}`}
              >
                <div>
                  <Label>Question</Label>
                  <Input
                    value={f.q}
                    onChange={(e) => updateItem('faqs', i, 'q', e.target.value)}
                  />
                </div>
                <div>
                  <Label>Answer</Label>
                  <Textarea
                    rows={3}
                    value={f.a}
                    onChange={(e) => updateItem('faqs', i, 'a', e.target.value)}
                  />
                </div>
                <div className="flex justify-end">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => removeItem('faqs', i)}
                    data-testid={`remove-faq-${i}`}
                  >
                    <Trash2 className="w-4 h-4 mr-1" /> Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ============================== Who it's for ========================== */}
      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <SectionTitle hint="One bullet per item">
              Who this course is for
            </SectionTitle>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => addString('who_for')}
              data-testid="add-who-for-btn"
            >
              <Plus className="w-4 h-4 mr-1" /> Add
            </Button>
          </div>
          <div className="space-y-2">
            {v.who_for.map((s, i) => (
              <div key={i} className="flex gap-2" data-testid={`who-for-row-${i}`}>
                <Input
                  value={s}
                  onChange={(e) => updateString('who_for', i, e.target.value)}
                  placeholder="Beginners switching into tech"
                />
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  onClick={() => removeString('who_for', i)}
                  data-testid={`remove-who-for-${i}`}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ============================== Requirements ========================== */}
      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <SectionTitle hint="One requirement per item">Requirements</SectionTitle>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => addString('requirements')}
              data-testid="add-requirement-btn"
            >
              <Plus className="w-4 h-4 mr-1" /> Add
            </Button>
          </div>
          <div className="space-y-2">
            {v.requirements.map((s, i) => (
              <div
                key={i}
                className="flex gap-2"
                data-testid={`requirement-row-${i}`}
              >
                <Input
                  value={s}
                  onChange={(e) => updateString('requirements', i, e.target.value)}
                  placeholder="A laptop with stable internet"
                />
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  onClick={() => removeString('requirements', i)}
                  data-testid={`remove-requirement-${i}`}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default CourseLandingFields;
