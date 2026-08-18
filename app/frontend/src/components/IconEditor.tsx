import { useState, useEffect, useRef } from 'react';
import { getIconList, generateIcon, updateIcon, deleteIcon, getIconUrl } from '../api/client';
import type { IconInfo } from '../api/client';

const SIZE_OPTIONS = [
  { name: 'small', label: 'Small (96px)' },
  { name: 'medium', label: 'Medium (128px)' },
  { name: 'large', label: 'Large (160px)' },
];

interface Props {
  onIconsChanged: () => void;
}

export default function IconEditor({ onIconsChanged }: Props) {
  const [icons, setIcons] = useState<IconInfo[]>([]);
  const [selectedIcon, setSelectedIcon] = useState<IconInfo | null>(null);
  const [newId, setNewId] = useState('');
  const [newPrompt, setNewPrompt] = useState('');
  const [newSize, setNewSize] = useState('medium');
  const [generating, setGenerating] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const confirmDeleteRef = useRef<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [previewKey, setPreviewKey] = useState(0);

  const fetchIcons = async () => {
    try {
      const list = await getIconList();
      setIcons(list);
    } catch (err) {
      console.error('Failed to fetch icons:', err);
    }
  };

  useEffect(() => {
    fetchIcons();
  }, []);

  const handleSelectIcon = (icon: IconInfo) => {
    setSelectedIcon(icon);
    confirmDeleteRef.current = null;
    setConfirmDeleteId(null);
  };

  const handleGenerate = async () => {
    const id = newId.trim().toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_');
    if (!id || !newPrompt.trim()) return;
    setGenerating(true);
    try {
      const created = await generateIcon(id, newPrompt.trim(), newSize);
      setNewId('');
      setNewPrompt('');
      await fetchIcons();
      onIconsChanged();
      setPreviewKey((k) => k + 1);
      setSelectedIcon(created);
    } catch (err) {
      console.error('Failed to generate icon:', err);
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!selectedIcon) return;
    try {
      const updated = await updateIcon(selectedIcon.id, {
        prompt: selectedIcon.prompt,
        size: selectedIcon.size,
      });
      await fetchIcons();
      onIconsChanged();
      setSelectedIcon(updated);
    } catch (err) {
      console.error('Failed to save icon:', err);
    }
  };

  const handleRegenerate = async () => {
    if (!selectedIcon) return;
    setRegenerating(true);
    try {
      const updated = await generateIcon(selectedIcon.id, selectedIcon.prompt, selectedIcon.size);
      await fetchIcons();
      onIconsChanged();
      setPreviewKey((k) => k + 1);
      setSelectedIcon(updated);
    } catch (err) {
      console.error('Failed to regenerate icon:', err);
    } finally {
      setRegenerating(false);
    }
  };

  const handleCopyToNew = () => {
    if (!selectedIcon) return;
    setNewId('');
    setNewPrompt(selectedIcon.prompt);
    setNewSize(selectedIcon.size);
    setSelectedIcon(null);
  };

  const handleDelete = async (iconId: string) => {
    if (confirmDeleteRef.current !== iconId) {
      confirmDeleteRef.current = iconId;
      setConfirmDeleteId(iconId);
      return;
    }
    try {
      await deleteIcon(iconId);
      confirmDeleteRef.current = null;
      setConfirmDeleteId(null);
      if (selectedIcon?.id === iconId) setSelectedIcon(null);
      setIcons((prev) => prev.filter((i) => i.id !== iconId));
      onIconsChanged();
    } catch (err) {
      console.error('Failed to delete icon:', err);
    }
  };

  const updateSelectedField = (field: string, value: unknown) => {
    if (!selectedIcon) return;
    setSelectedIcon({ ...selectedIcon, [field]: value });
  };

  return (
    <div>
      <h3 className="deck-editor-title">Icon Editor</h3>

      {/* Icon grid */}
      <div className="icon-grid">
        {icons.map((icon) => (
          <div
            key={icon.id}
            className={`icon-card ${selectedIcon?.id === icon.id ? 'icon-card-selected' : ''}`}
            onClick={() => handleSelectIcon(icon)}
          >
            <img
              src={`${getIconUrl(icon.id)}?v=${previewKey}`}
              alt={icon.id}
              className="icon-card-image"
            />
            <div className="icon-card-name">{icon.id}</div>
            <div className="icon-card-size">{icon.size}</div>
            <button
              className={`icon-card-delete ${confirmDeleteId === icon.id ? 'confirming' : ''}`}
              onClick={(e) => { e.stopPropagation(); handleDelete(icon.id); }}
            >
              {confirmDeleteId === icon.id ? 'Delete?' : 'x'}
            </button>
          </div>
        ))}
      </div>

      {/* Selected icon detail */}
      {selectedIcon && (
        <div className="icon-detail-section">
          <div className="icon-detail-header">
            <img
              src={`${getIconUrl(selectedIcon.id)}?v=${previewKey}`}
              alt={selectedIcon.id}
              className="icon-detail-image"
            />
            <div>
              <div className="icon-detail-name">{selectedIcon.id}</div>
              <div className="icon-detail-hint">
                {selectedIcon.size} ({selectedIcon.size_px}px on card)
              </div>
            </div>
          </div>
          <div className="form-group">
            <label>Art Prompt</label>
            <textarea
              className="tall"
              value={selectedIcon.prompt}
              onChange={(e) => updateSelectedField('prompt', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Size on Card</label>
            <div className="size-picker">
              {SIZE_OPTIONS.map((opt) => (
                <button
                  key={opt.name}
                  className={`size-btn ${selectedIcon.size === opt.name ? 'size-btn-active' : ''}`}
                  onClick={() => updateSelectedField('size', opt.name)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div className="editor-actions">
            <button
              className="btn btn-save"
              onClick={handleSave}
            >
              Save
            </button>
            <button
              className="btn btn-generate"
              disabled={regenerating || !selectedIcon.prompt.trim()}
              onClick={handleRegenerate}
            >
              {regenerating && <span className="spinner" />}
              {regenerating ? 'Regenerating...' : 'Regenerate Art'}
            </button>
            <button className="btn btn-secondary" onClick={handleCopyToNew}>
              Copy to New
            </button>
          </div>
        </div>
      )}

      {/* Create new icon */}
      <div className="icon-create-section">
        <h4 className="icon-section-title">Create New Icon</h4>
        <div className="form-group">
          <label>Icon Name</label>
          <input
            type="text"
            value={newId}
            onChange={(e) => setNewId(e.target.value)}
            placeholder="e.g. shield, fuel, wrench"
          />
        </div>
        <div className="form-group">
          <label>Art Prompt</label>
          <textarea
            className="tall"
            value={newPrompt}
            onChange={(e) => setNewPrompt(e.target.value)}
            placeholder="Single cartoon icon on a solid white background, fun cartoon game icon style, clean simple bold design, centered, no text, bright vivid colors, game UI icon, white background"
          />
        </div>
        <div className="form-group">
          <label>Size on Card</label>
          <div className="size-picker">
            {SIZE_OPTIONS.map((opt) => (
              <button
                key={opt.name}
                className={`size-btn ${newSize === opt.name ? 'size-btn-active' : ''}`}
                onClick={() => setNewSize(opt.name)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <button
          className="btn btn-generate"
          style={{ width: '100%' }}
          disabled={generating || !newId.trim() || !newPrompt.trim()}
          onClick={handleGenerate}
        >
          {generating && <span className="spinner" />}
          {generating ? 'Generating Icon...' : 'Generate New Icon'}
        </button>
      </div>
    </div>
  );
}
