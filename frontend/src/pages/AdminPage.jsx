import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Plus, Trash2, Check, X, Mail } from "lucide-react";
import { toast } from "sonner";

function StatCard({ label, value, sub }) {
  return (
    <div className="border border-black/10 bg-white p-5">
      <div className="eyebrow mb-2">{label}</div>
      <div className="font-display text-4xl tracking-tighter">{value}</div>
      {sub && <div className="text-xs text-[color:var(--text-muted)] mt-2">{sub}</div>}
    </div>
  );
}

export default function AdminPage() {
  const [tab, setTab] = useState("overview");
  const [stats, setStats] = useState(null);
  const [courses, setCourses] = useState([]);
  const [users, setUsers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [testimonials, setTestimonials] = useState([]);
  const [lessons, setLessons] = useState({}); // courseId -> lessons[]
  const [openCourse, setOpenCourse] = useState(false);
  const [openLesson, setOpenLesson] = useState(false);
  const [activeCourseId, setActiveCourseId] = useState(null);

  // course form
  const [courseForm, setCourseForm] = useState({
    title: "",
    short_description: "",
    description: "",
    category: "Design",
    level: "beginner",
    price: 0,
    thumbnail_url: "",
    tags: "",
    is_published: true,
  });
  // lesson form
  const [lessonForm, setLessonForm] = useState({
    title: "",
    description: "",
    content_text: "",
    video_url: "",
    duration_minutes: 10,
    order: 0,
    is_preview: false,
  });

  const refreshAll = async () => {
    const [s, c, u, p, ct, t] = await Promise.all([
      api.get("/admin/stats"),
      api.get("/courses", { params: { is_published: undefined } }),
      api.get("/admin/users"),
      api.get("/admin/payments"),
      api.get("/contacts"),
      api.get("/testimonials", { params: { is_approved: undefined } }),
    ]);
    setStats(s.data);
    setCourses(c.data);
    setUsers(u.data);
    setPayments(p.data);
    setContacts(ct.data);
    setTestimonials(t.data);
  };

  useEffect(() => {
    refreshAll();
  }, []);

  useEffect(() => {
    // load lessons for all courses (for admin)
    (async () => {
      const m = {};
      for (const c of courses) {
        try {
          const { data } = await api.get(`/lessons/by-course/${c.id}`);
          m[c.id] = data;
        } catch {
          m[c.id] = [];
        }
      }
      setLessons(m);
    })();
  }, [courses]);

  const saveCourse = async () => {
    try {
      const payload = {
        ...courseForm,
        price: Number(courseForm.price) || 0,
        tags: courseForm.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      };
      await api.post("/courses", payload);
      toast.success("Course created");
      setOpenCourse(false);
      setCourseForm({ ...courseForm, title: "", description: "", short_description: "" });
      refreshAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  };

  const saveLesson = async () => {
    try {
      await api.post("/lessons", { ...lessonForm, course_id: activeCourseId, duration_minutes: Number(lessonForm.duration_minutes) || 0, order: Number(lessonForm.order) || 0 });
      toast.success("Lesson added");
      setOpenLesson(false);
      setLessonForm({ ...lessonForm, title: "", description: "", content_text: "", video_url: "" });
      const { data } = await api.get(`/lessons/by-course/${activeCourseId}`);
      setLessons((m) => ({ ...m, [activeCourseId]: data }));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  };

  const togglePublish = async (course) => {
    await api.patch(`/courses/${course.id}`, { is_published: !course.is_published });
    toast.success(!course.is_published ? "Published" : "Unpublished");
    refreshAll();
  };

  const deleteCourse = async (id) => {
    if (!window.confirm("Delete this course and all its lessons?")) return;
    await api.delete(`/courses/${id}`);
    toast.success("Course deleted");
    refreshAll();
  };

  const deleteLesson = async (lessonId, courseId) => {
    await api.delete(`/lessons/${lessonId}`);
    const { data } = await api.get(`/lessons/by-course/${courseId}`);
    setLessons((m) => ({ ...m, [courseId]: data }));
    toast.success("Lesson deleted");
  };

  const approveTestimonial = async (id, value) => {
    await api.patch(`/testimonials/${id}`, { is_approved: value, is_featured: value });
    refreshAll();
  };

  const markContactRead = async (id) => {
    await api.patch(`/contacts/${id}/read`);
    refreshAll();
  };

  return (
    <div data-testid="admin-page" className="max-w-[1400px] mx-auto px-6 md:px-10 lg:px-16 py-10">
      <div className="mb-8">
        <div className="eyebrow mb-3">Admin · Studio Operations</div>
        <h1 className="font-display text-4xl sm:text-5xl tracking-tighter leading-none">Control room.</h1>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList data-testid="admin-tabs" className="bg-transparent gap-2 p-0 mb-6 flex-wrap h-auto">
          {["overview", "courses", "users", "payments", "contacts", "testimonials"].map((t) => (
            <TabsTrigger
              key={t}
              value={t}
              data-testid={`admin-tab-${t}`}
              className="capitalize rounded-none border border-black/15 data-[state=active]:bg-[color:var(--accent)] data-[state=active]:text-white px-4 py-2"
            >
              {t}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="overview">
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Users" value={stats.users} sub={`${stats.students} students`} />
              <StatCard label="Courses" value={stats.courses} sub={`${stats.published_courses} published`} />
              <StatCard label="Enrollments" value={stats.enrollments} sub={`${stats.completed_enrollments} completed`} />
              <StatCard
                label="Revenue"
                value={`₦${(stats.revenue || 0).toLocaleString()}`}
                sub={`${stats.successful_payments} payments`}
              />
            </div>
          )}
        </TabsContent>

        <TabsContent value="courses">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-display text-2xl">Courses & Lessons</h3>
            <Dialog open={openCourse} onOpenChange={setOpenCourse}>
              <DialogTrigger asChild>
                <button data-testid="admin-new-course" className="btn-primary text-sm py-2 px-4">
                  <Plus className="w-4 h-4" strokeWidth={1.5} /> New course
                </button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl rounded-none">
                <DialogHeader>
                  <DialogTitle>New course</DialogTitle>
                </DialogHeader>
                <div className="grid grid-cols-2 gap-4 mt-2">
                  <div className="col-span-2">
                    <Label>Title</Label>
                    <Input value={courseForm.title} onChange={(e) => setCourseForm({ ...courseForm, title: e.target.value })} />
                  </div>
                  <div className="col-span-2">
                    <Label>Short description</Label>
                    <Input value={courseForm.short_description} onChange={(e) => setCourseForm({ ...courseForm, short_description: e.target.value })} />
                  </div>
                  <div className="col-span-2">
                    <Label>Description</Label>
                    <Textarea rows={4} value={courseForm.description} onChange={(e) => setCourseForm({ ...courseForm, description: e.target.value })} />
                  </div>
                  <div>
                    <Label>Category</Label>
                    <Input value={courseForm.category} onChange={(e) => setCourseForm({ ...courseForm, category: e.target.value })} />
                  </div>
                  <div>
                    <Label>Level</Label>
                    <Select value={courseForm.level} onValueChange={(v) => setCourseForm({ ...courseForm, level: v })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="beginner">Beginner</SelectItem>
                        <SelectItem value="intermediate">Intermediate</SelectItem>
                        <SelectItem value="advanced">Advanced</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Price (₦, 0 = free)</Label>
                    <Input type="number" value={courseForm.price} onChange={(e) => setCourseForm({ ...courseForm, price: e.target.value })} />
                  </div>
                  <div>
                    <Label>Thumbnail URL</Label>
                    <Input value={courseForm.thumbnail_url} onChange={(e) => setCourseForm({ ...courseForm, thumbnail_url: e.target.value })} />
                  </div>
                  <div className="col-span-2">
                    <Label>Tags (comma separated)</Label>
                    <Input value={courseForm.tags} onChange={(e) => setCourseForm({ ...courseForm, tags: e.target.value })} />
                  </div>
                  <div className="col-span-2 flex items-center justify-between">
                    <Label>Publish immediately</Label>
                    <Switch checked={courseForm.is_published} onCheckedChange={(v) => setCourseForm({ ...courseForm, is_published: v })} />
                  </div>
                </div>
                <DialogFooter>
                  <button onClick={saveCourse} className="btn-primary">Create course</button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="space-y-4">
            {courses.map((c) => (
              <div key={c.id} className="border border-black/10 bg-white">
                <div className="p-5 flex items-center justify-between gap-4 flex-wrap">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span className={`inline-block w-2 h-2 ${c.is_published ? "bg-[color:var(--success)]" : "bg-[color:var(--text-muted)]"}`} />
                      <div className="font-display text-xl">{c.title}</div>
                    </div>
                    <div className="text-xs text-[color:var(--text-muted)] mt-1 font-mono">
                      {c.category} · {c.level} · {c.price > 0 ? `₦${c.price.toLocaleString()}` : "Free"} · {(lessons[c.id] || []).length} lessons
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      data-testid={`admin-toggle-${c.id}`}
                      onClick={() => togglePublish(c)}
                      className="text-xs px-3 py-1.5 border border-black/15 hover:border-[color:var(--accent)]"
                    >
                      {c.is_published ? "Unpublish" : "Publish"}
                    </button>
                    <button
                      data-testid={`admin-add-lesson-${c.id}`}
                      onClick={() => {
                        setActiveCourseId(c.id);
                        setLessonForm({ ...lessonForm, order: (lessons[c.id]?.length || 0) + 1 });
                        setOpenLesson(true);
                      }}
                      className="text-xs px-3 py-1.5 border border-black/15 hover:border-[color:var(--accent)]"
                    >
                      + Lesson
                    </button>
                    <button
                      data-testid={`admin-delete-course-${c.id}`}
                      onClick={() => deleteCourse(c.id)}
                      className="p-2 text-[color:var(--error)] hover:bg-red-50"
                    >
                      <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                    </button>
                  </div>
                </div>
                {(lessons[c.id] || []).length > 0 && (
                  <ol className="border-t border-black/10">
                    {lessons[c.id].map((l, i) => (
                      <li key={l.id} className="flex items-center justify-between text-sm px-5 py-2 border-b border-black/5 last:border-b-0">
                        <span>
                          <span className="font-mono text-xs text-[color:var(--text-muted)] mr-3">{String(i + 1).padStart(2, "0")}</span>
                          {l.title}
                        </span>
                        <button
                          data-testid={`admin-delete-lesson-${l.id}`}
                          onClick={() => deleteLesson(l.id, c.id)}
                          className="text-[color:var(--text-muted)] hover:text-[color:var(--error)]"
                        >
                          <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                        </button>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            ))}
          </div>

          <Dialog open={openLesson} onOpenChange={setOpenLesson}>
            <DialogContent className="max-w-2xl rounded-none">
              <DialogHeader>
                <DialogTitle>Add lesson</DialogTitle>
              </DialogHeader>
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label>Title</Label>
                  <Input value={lessonForm.title} onChange={(e) => setLessonForm({ ...lessonForm, title: e.target.value })} />
                </div>
                <div className="col-span-2">
                  <Label>Description</Label>
                  <Input value={lessonForm.description} onChange={(e) => setLessonForm({ ...lessonForm, description: e.target.value })} />
                </div>
                <div className="col-span-2">
                  <Label>Video URL (YouTube embed, Vimeo, mp4…)</Label>
                  <Input value={lessonForm.video_url} onChange={(e) => setLessonForm({ ...lessonForm, video_url: e.target.value })} />
                </div>
                <div className="col-span-2">
                  <Label>Content (text)</Label>
                  <Textarea rows={4} value={lessonForm.content_text} onChange={(e) => setLessonForm({ ...lessonForm, content_text: e.target.value })} />
                </div>
                <div>
                  <Label>Duration (min)</Label>
                  <Input type="number" value={lessonForm.duration_minutes} onChange={(e) => setLessonForm({ ...lessonForm, duration_minutes: e.target.value })} />
                </div>
                <div>
                  <Label>Order</Label>
                  <Input type="number" value={lessonForm.order} onChange={(e) => setLessonForm({ ...lessonForm, order: e.target.value })} />
                </div>
                <div className="col-span-2 flex items-center justify-between">
                  <Label>Free preview lesson</Label>
                  <Switch checked={lessonForm.is_preview} onCheckedChange={(v) => setLessonForm({ ...lessonForm, is_preview: v })} />
                </div>
              </div>
              <DialogFooter>
                <button onClick={saveLesson} className="btn-primary">Save lesson</button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </TabsContent>

        <TabsContent value="users">
          <table className="w-full text-sm">
            <thead className="border-b border-black/10">
              <tr className="text-left text-xs uppercase tracking-wider text-[color:var(--text-muted)]">
                <th className="py-3">Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Joined</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-black/5">
                  <td className="py-3">{u.name}</td>
                  <td>{u.email}</td>
                  <td>
                    <span className={`text-[10px] uppercase tracking-wider px-2 py-1 ${u.role === "admin" ? "bg-[color:var(--accent)] text-white" : "border border-black/15"}`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="text-[color:var(--text-muted)] text-xs">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TabsContent>

        <TabsContent value="payments">
          <table className="w-full text-sm">
            <thead className="border-b border-black/10">
              <tr className="text-left text-xs uppercase tracking-wider text-[color:var(--text-muted)]">
                <th className="py-3">Reference</th>
                <th>Email</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {payments.length === 0 && (
                <tr><td colSpan={5} className="py-8 text-center text-[color:var(--text-muted)]">No payments yet.</td></tr>
              )}
              {payments.map((p) => (
                <tr key={p.id} className="border-b border-black/5">
                  <td className="py-3 font-mono text-xs">{p.reference}</td>
                  <td>{p.email}</td>
                  <td>₦{p.amount.toLocaleString()}</td>
                  <td>
                    <span className={`text-[10px] uppercase tracking-wider px-2 py-1 ${p.status === "success" ? "bg-[color:var(--success)] text-white" : p.status === "failed" ? "bg-[color:var(--error)] text-white" : "border border-black/15"}`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="text-[color:var(--text-muted)] text-xs">{new Date(p.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TabsContent>

        <TabsContent value="contacts">
          <div className="space-y-3">
            {contacts.length === 0 && (
              <p className="text-[color:var(--text-muted)] py-8 text-center">No messages yet.</p>
            )}
            {contacts.map((c) => (
              <div key={c.id} className={`border border-black/10 bg-white p-5 ${!c.is_read ? "border-l-4 border-l-[color:var(--accent)]" : ""}`}>
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <div className="font-semibold flex items-center gap-2">
                      <Mail className="w-4 h-4" strokeWidth={1.5} /> {c.name} <span className="text-[color:var(--text-muted)] font-normal">· {c.email}</span>
                    </div>
                    {c.subject && <div className="text-sm text-[color:var(--text-muted)] mt-1">{c.subject}</div>}
                  </div>
                  {!c.is_read && (
                    <button
                      onClick={() => markContactRead(c.id)}
                      data-testid={`mark-read-${c.id}`}
                      className="text-xs px-3 py-1.5 border border-black/15"
                    >
                      Mark read
                    </button>
                  )}
                </div>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{c.message}</p>
                <div className="text-xs text-[color:var(--text-muted)] mt-3">{new Date(c.created_at).toLocaleString()}</div>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="testimonials">
          <div className="space-y-3">
            {testimonials.length === 0 && (
              <p className="text-[color:var(--text-muted)] py-8 text-center">No testimonials yet.</p>
            )}
            {testimonials.map((t) => (
              <div key={t.id} className="border border-black/10 bg-white p-5 flex items-start gap-4">
                <div className="flex-1">
                  <p className="text-sm leading-relaxed mb-3">"{t.quote}"</p>
                  <div className="text-xs text-[color:var(--text-muted)]">
                    {t.name} {t.role && `· ${t.role}`} · Rating: {t.rating}/5
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => approveTestimonial(t.id, !t.is_approved)}
                    data-testid={`approve-testimonial-${t.id}`}
                    className={`text-xs px-3 py-1.5 border ${t.is_approved ? "border-[color:var(--success)] text-[color:var(--success)]" : "border-black/15"}`}
                  >
                    {t.is_approved ? <><Check className="w-3 h-3 inline" strokeWidth={1.5} /> Approved</> : <><X className="w-3 h-3 inline" strokeWidth={1.5} /> Pending</>}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
