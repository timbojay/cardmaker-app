import { useState, useEffect, useRef } from 'react';
import { getBackgrounds, generateBackground, deleteBackground, getBackgroundUrl } from '../api/client';
import type { Background } from '../types';

interface Props {
  onBackgroundsChanged: () => void;
}

export default function BackgroundEditor({ onBackgroundsChanged }: Props) {
  const [backgrounds, setBackgrounds] = useState<Background[]>([]);
  const [selectedBg, setSelectedBg] = useState<Background | null>(null);
  const [newId, setNewId] = useState('');
  const [newPrompt, setNewPrompt] = useState('');
  const [newColor, setNewColor] = useState('#966943');
  const [newAccent, setNewAccent] = useState('#c8963c');
  const [generating, setGenerating] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const confirmDeleteRef = useRef<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [previewKey, setPreviewKey] = useState(0);

  const fetchBackgrounds = async () => {
    try {
      const list = await getBackgrounds();
      setBackgrounds(list);
    } catch (err) {
      console.error('Failed to fetch backgrounds:', err);
    }
  };

  useEffect(() => {
    fetchBackgrounds();
  }, []);

  const hexToRgb = (hex: string): number[] => {
    const h = hex.replace('#', '');
    return [parseInt(h.substring(0, 2), 16), parseInt(h.substring(2, 4), 16), parseInt(h.substring(4, 6), 16)];
  };

  const rgbToHex = (rgb: number[]): string => {
    return '#' + rgb.map((c) => c.toString(16).padStart(2, '0')).join('');
  };

  const handleGenerate = async () => {
    const id = newId.trim().toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_');
    if (!id || !newPrompt.trim()) return;
    setGenerating(true);
    try {
      const created = await generateBackground({
        id,
        prompt: newPrompt.trim(),
        border_color: hexToRgb(newColor),
        border_accent: hexToRgb(newAccent),
      });
      setNewId('');
      setNewPrompt('');
      await fetchBackgrounds();
      onBackgroundsChanged();
      setPreviewKey((k) => k + 1);
      setSelectedBg(created);
    } catch (err) {
      console.error('Failed to generate background:', err);
    } finally {
      setGenerating(false);
    }
  };

  const handleRegenerate = async () => {
    if (!selectedBg) return;
    setRegenerating(true);
    try {
      const updated = await generateBackground({
        id: selectedBg.id,
        prompt: selectedBg.prompt,
        border_color: selectedBg.border_color,
        border_accent: selectedBg.border_accent,
      });
      await fetchBackgrounds();
      onBackgroundsChanged();
      setPreviewKey((k) => k + 1);
      setSelectedBg(updated);
    } catch (err) {
      console.error('Failed to regenerate background:', err);
    } finally {
      setRegenerating(false);
    }
  };

  const handleCopyToNew = () => {
    if (!selectedBg) return;
    setNewId('');
    setNewPrompt(selectedBg.prompt);
    setNewColor(rgbToHex(selectedBg.border_color));
    setNewAccent(rgbToHex(selectedBg.border_accent));
    setSelectedBg(null);
  };

  const handleDelete = async (bgId: string) => {
    if (confirmDeleteRef.current !== bgId) {
      confirmDeleteRef.current = bgId;
      setConfirmDeleteId(bgId);
      return;
    }
    try {
      await deleteBackground(bgId);
      confirmDeleteRef.current = null;
      setConfirmDeleteId(null);
      if (selectedBg?.id === bgId) setSelectedBg(null);
      setBackgrounds((prev) => prev.filter((b) => b.id !== bgId));
      onBackgroundsChanged();
    } catch (err) {
      console.error('Failed to delete background:', err);
    }
  };

  const updateSelectedField = (field: string, value: unknown) => {
    if (!selectedBg) return;
    setSelectedBg({ ...selectedBg, [field]: value });
  };

  return (
    <div>
      <h3 className="deck-editor-title">Background Editor</h3>

      {/* Background grid */}
      <div className="bg-grid">
        {backgrounds.map((bg) => (
          <div
            key={bg.id}
            className={`bg-card ${selectedBg?.id === bg.id ? 'bg-card-selected' : ''}`}
            onClick={() => setSelectedBg(bg)}
          >
            <img
              src={`${getBackgroundUrl(bg.id)}?v=${previewKey}`}
              alt={bg.id}
              className="bg-card-image"
            />
            <div className="bg-card-name">{bg.id}</div>
            <button
              className={`icon-card-delete ${confirmDeleteId === bg.id ? 'confirming' : ''}`}
              onClick={(e) => { e.stopPropagation(); handleDelete(bg.id); }}
            >
              {confirmDeleteId === bg.id ? 'Delete?' : 'x'}
            </button>
          </div>
        ))}
      </div>

      {/* Selected background detail */}
      {selectedBg && (
        <div className="icon-detail-section">
          <div className="icon-detail-header">
            <img
              src={`${getBackgroundUrl(selectedBg.id)}?v=${previewKey}`}
              alt={selectedBg.id}
              className="bg-detail-image"
            />
            <div>
              <div className="icon-detail-name">{selectedBg.id}</div>
              <div className="icon-detail-hint">Edit prompt/colors and regenerate</div>
            </div>
          </div>
          <div className="form-group">
            <label>Art Prompt</label>
            <textarea
              className="tall"
              value={selectedBg.prompt}
              onChange={(e) => updateSelectedField('prompt', e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Border Color</label>
              <input
                type="color"
                value={rgbToHex(selectedBg.border_color)}
                onChange={(e) => updateSelectedField('border_color', hexToRgb(e.target.value))}
                style={{ width: '100%', height: 36 }}
              />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Accent Color</label>
              <input
                type="color"
                value={rgbToHex(selectedBg.border_accent)}
                onChange={(e) => updateSelectedField('border_accent', hexToRgb(e.target.value))}
                style={{ width: '100%', height: 36 }}
              />
            </div>
          </div>
          <div className="editor-actions">
            <button
              className="btn btn-generate"
              disabled={regenerating || !selectedBg.prompt.trim()}
              onClick={handleRegenerate}
              style={{ flex: 1 }}
            >
              {regenerating && <span className="spinner" />}
              {regenerating ? 'Regenerating...' : 'Regenerate'}
            </button>
            <button className="btn btn-secondary" onClick={handleCopyToNew}>
              Copy to New
            </button>
          </div>
        </div>
      )}

      {/* Create new background */}
      <div className="icon-create-section">
        <h4 className="icon-section-title">Create New Background</h4>
        <div className="form-group">
          <label>Background Name</label>
          <input
            type="text"
            value={newId}
            onChange={(e) => setNewId(e.target.value)}
            placeholder="e.g. hazard, cosmic, steampunk"
          />
        </div>
        <div className="form-group">
          <label>Art Prompt</label>
          <textarea
            className="tall"
            value={newPrompt}
            onChange={(e) => setNewPrompt(e.target.value)}
            placeholder="Cartoon seamless border pattern of ..., fun cartoon style, bright colors, white background in center, game card border"
          />
        </div>
        <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Border Color</label>
            <input
              type="color"
              value={newColor}
              onChange={(e) => setNewColor(e.target.value)}
              style={{ width: '100%', height: 36 }}
            />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Accent Color</label>
            <input
              type="color"
              value={newAccent}
              onChange={(e) => setNewAccent(e.target.value)}
              style={{ width: '100%', height: 36 }}
            />
          </div>
        </div>
        <button
          className="btn btn-generate"
          style={{ width: '100%' }}
          disabled={generating || !newId.trim() || !newPrompt.trim()}
          onClick={handleGenerate}
        >
          {generating && <span className="spinner" />}
          {generating ? 'Generating Background...' : 'Generate New Background'}
        </button>
      </div>
    </div>
  );
}
