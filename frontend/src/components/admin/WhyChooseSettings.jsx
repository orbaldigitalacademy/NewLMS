import React, { useState, useEffect } from 'react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Plus, Trash2, Save } from 'lucide-react';
import { settingsAPI } from '../services/api';
import { toast } from 'sonner';

/*
  WhyChooseSettings
  -----------------
  Admin form for editing the "Why Choose Orbal Academy" items stored on
  site settings.

  Backend contract:
    GET  settingsAPI.get()         -> { data: { why_choose_items: [...] } }
    PUT  settingsAPI.update(body)  -> updates the settings document

  Each item shape:
    { icon: string, title: string, description: string }

  `icon` is a lucide-react icon name. The frontend landing page maps a small
  set of allowed names; anything outside the allowed set falls back to a
  default icon. Allowed names (must match the landing page mapping):
    "Rocket", "HeartHandshake", "ShieldCheck", "Lightbulb",
    "Sparkles", "Target", "Award", "GraduationCap"
*/

const ALLOWED_ICONS = [
  'Rocket',
  'HeartHandshake',
  'ShieldCheck',
  'Lightbulb',
  'Sparkles',
  'Target',
  'Award',
  'GraduationCap',
];

const emptyItem = { icon: 'Rocket', title: '', description: '' };

const WhyChooseSettings = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await settingsAPI.get();
        setItems(res.data?.why_choose_items || []);
      } catch (err) {
        console.error('Failed to load settings', err);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const addItem = () => setItems([...items, { ...emptyItem }]);
  const removeItem = (i) => setItems(items.filter((_, idx) => idx !== i));
  const updateItem = (i, field, val) =>
    setItems(items.map((it, idx) => (idx === i ? { ...it, [field]: val } : it)));

  const handleSave = async () => {
    setSaving(true);
    try {
      await settingsAPI.update({ why_choose_items: items });
      toast.success('Saved');
    } catch (err) {
      console.error(err);
      toast.error('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-2xl font-bold text-secondary">
            Why Choose Orbal Academy
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Items shown in the "Why Choose Orbal Academy" section on every course page.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={addItem}
          data-testid="add-why-choose-item-btn"
        >
          <Plus className="w-4 h-4 mr-1" /> Add item
        </Button>
      </div>

      {items.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No items yet. Courses will fall back to the built-in defaults.
        </p>
      )}

      <div className="space-y-4">
        {items.map((item, i) => (
          <Card key={i} data-testid={`why-choose-row-${i}`}>
            <CardContent className="p-5 space-y-3">
              <div className="grid md:grid-cols-[160px_1fr] gap-3">
                <div>
                  <Label>Icon</Label>
                  <select
                    value={item.icon || 'Rocket'}
                    onChange={(e) => updateItem(i, 'icon', e.target.value)}
                    className="w-full h-10 px-3 border border-input bg-background rounded-md text-sm"
                    data-testid={`why-choose-icon-${i}`}
                  >
                    {ALLOWED_ICONS.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label>Title</Label>
                  <Input
                    value={item.title}
                    onChange={(e) => updateItem(i, 'title', e.target.value)}
                    placeholder="Project-first learning"
                    data-testid={`why-choose-title-${i}`}
                  />
                </div>
              </div>
              <div>
                <Label>Description</Label>
                <Textarea
                  rows={2}
                  value={item.description}
                  onChange={(e) => updateItem(i, 'description', e.target.value)}
                  placeholder="Short, punchy line describing this benefit."
                  data-testid={`why-choose-description-${i}`}
                />
              </div>
              <div className="flex justify-end">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => removeItem(i)}
                  data-testid={`remove-why-choose-${i}`}
                >
                  <Trash2 className="w-4 h-4 mr-1" /> Remove
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex justify-end">
        <Button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="rounded-full px-6"
          data-testid="save-why-choose-btn"
        >
          <Save className="w-4 h-4 mr-2" />
          {saving ? 'Saving…' : 'Save changes'}
        </Button>
      </div>
    </div>
  );
};

export default WhyChooseSettings;
