import { useState, useEffect } from 'react';
import type { Card, Deck, Background, UpdateCardData } from '../types';
import { updateCard, deleteCard, generateCard, recompositeCard, getCardPreviewUrl, getBackgroundUrl } from '../api/client';

interface ResourceEntry {
  icon: string;
  count: number;
}

function recordToEntries(record: Record<string, number>): ResourceEntry[] {
  return Object.entries(record).map(([icon, count]) => ({ icon, count }));
}

function entriesToRecord(entries: ResourceEntry[]): Record<string, number> {
  const result: Record<string, number> = {};
  for (const e of entries) {
    if (e.icon) result[e.icon] = e.count;
  }
  return result;
}

interface Props {
  card: Card;
  decks: Deck[];
  backgrounds: Background[];
  icons: string[];
  onCardUpdated: () => void;
  onCardDeleted: () => void;
}

export default function CardEditor({
  card,
  decks,
  backgrounds,
  icons,
  onCardUpdated,
  onCardDeleted,
}: Props) {
  const [title, setTitle] = useState(card.title);
  const [deckId, setDeckId] = useState(card.deck_id);
  const [backgroundId, setBackgroundId] = useState(card.background_id || '');
  const [description, setDescription] = useState(card.description);
  const [artPrompt, setArtPrompt] = useState(card.art_prompt);
  const [titleSize, setTitleSize] = useState(card.title_size || 'medium');
  const [descSize, setDescSize] = useState(card.desc_size || 'medium');
  const [showPlus, setShowPlus] = useState(card.show_plus !== false);
  const [showMinus, setShowMinus] = useState(card.show_minus !== false);
  const [benefits, setBenefits] = useState<ResourceEntry[]>(recordToEntries(card.benefits));
  const [costs, setCosts] = useState<ResourceEntry[]>(recordToEntries(card.costs));
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [recompositing, setRecompositing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [previewKey, setPreviewKey] = useState(0);

  // Reset form when card changes
  useEffect(() => {
    setTitle(card.title);
    setDeckId(card.deck_id);
    setBackgroundId(card.background_id || '');
    setDescription(card.description);
    setArtPrompt(card.art_prompt);
    setTitleSize(card.title_size || 'medium');
    setDescSize(card.desc_size || 'medium');
    setShowPlus(card.show_plus !== false);
    setShowMinus(card.show_minus !== false);
    setBenefits(recordToEntries(card.benefits));
    setCosts(recordToEntries(card.costs));
    setConfirmDelete(false);
    setPreviewKey((k) => k + 1);
  }, [card]);

  const saveCurrentData = async () => {
    const data: UpdateCardData = {
      title,
      deck_id: deckId,
      background_id: backgroundId,
      description,
      art_prompt: artPrompt,
      title_size: titleSize,
      desc_size: descSize,
      show_plus: showPlus,
      show_minus: showMinus,
      benefits: entriesToRecord(benefits),
      costs: entriesToRecord(costs),
    };
    await updateCard(card.id, data);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveCurrentData();
      onCardUpdated();
      setPreviewKey((k) => k + 1);
    } catch (err) {
      console.error('Failed to save card:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await saveCurrentData();
      await generateCard(card.id);
      onCardUpdated();
      setPreviewKey((k) => k + 1);
    } catch (err) {
      console.error('Failed to generate art:', err);
    } finally {
      setGenerating(false);
    }
  };

  const handleRecomposite = async () => {
    setRecompositing(true);
    try {
      await saveCurrentData();
      await recompositeCard(card.id);
      onCardUpdated();
      setPreviewKey((k) => k + 1);
    } catch (err) {
      console.error('Failed to recomposite card:', err);
    } finally {
      setRecompositing(false);
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    try {
      await deleteCard(card.id);
      onCardDeleted();
    } catch (err) {
      console.error('Failed to delete card:', err);
    }
  };

  const updateBenefit = (index: number, field: 'icon' | 'count', value: string | number) => {
    setBenefits((prev) => prev.map((b, i) => (i === index ? { ...b, [field]: value } : b)));
  };

  const updateCost = (index: number, field: 'icon' | 'count', value: string | number) => {
    setCosts((prev) => prev.map((c, i) => (i === index ? { ...c, [field]: value } : c)));
  };

  const removeBenefit = (index: number) => {
    setBenefits((prev) => prev.filter((_, i) => i !== index));
  };

  const removeCost = (index: number) => {
    setCosts((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div>
      {/* Preview */}
      <div className="editor-preview">
        {card.preview_image_path ? (
          <img
            src={`${getCardPreviewUrl(card.id)}?v=${previewKey}`}
            alt={card.title}
          />
        ) : (
          <div className="editor-preview-placeholder">No preview available</div>
        )}
      </div>

      {/* Title */}
      <div className="form-group">
        <div className="label-with-size">
          <label>Title</label>
          <div className="size-picker">
            {['small', 'medium', 'large'].map((s) => (
              <button
                key={s}
                className={`size-btn${titleSize === s ? ' size-btn-active' : ''}`}
                onClick={() => setTitleSize(s)}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <input
          type="text"
          className="title-input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>

      {/* Deck & Background */}
      <div style={{ display: 'flex', gap: 10 }}>
        <div className="form-group" style={{ flex: 1 }}>
          <label>Deck</label>
          <select value={deckId} onChange={(e) => setDeckId(e.target.value)}>
            <option value="">Select...</option>
            {decks.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
        <div className="form-group" style={{ flex: 1 }}>
          <label>Background</label>
          <select value={backgroundId} onChange={(e) => setBackgroundId(e.target.value)}>
            <option value="">None</option>
            {backgrounds.map((bg) => (
              <option key={bg.id} value={bg.id}>{bg.id}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Background preview thumbnail */}
      {backgroundId && (
        <div className="bg-preview-thumb">
          <img src={getBackgroundUrl(backgroundId)} alt={backgroundId} />
        </div>
      )}

      {/* Description */}
      <div className="form-group">
        <div className="label-with-size">
          <label>Description</label>
          <div className="size-picker">
            {['small', 'medium', 'large'].map((s) => (
              <button
                key={s}
                className={`size-btn${descSize === s ? ' size-btn-active' : ''}`}
                onClick={() => setDescSize(s)}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Card description..."
        />
      </div>

      {/* Art Prompt */}
      <div className="form-group">
        <label>Art Prompt</label>
        <textarea
          className="tall"
          value={artPrompt}
          onChange={(e) => setArtPrompt(e.target.value)}
          placeholder="Describe the art to generate..."
        />
      </div>

      {/* Benefits */}
      <div className="form-group">
        <div className="resource-section-header">
          <label>Benefits</label>
          <div className="resource-section-options">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={showPlus}
                onChange={(e) => setShowPlus(e.target.checked)}
              />
              <span className="pm-indicator plus">+</span>
            </label>
            <button
              className="add-resource-btn"
              onClick={() => setBenefits((prev) => [...prev, { icon: '', count: 1 }])}
            >
              + Add Benefit
            </button>
          </div>
        </div>
        {benefits.map((b, i) => (
          <div className="resource-row" key={i}>
            <select value={b.icon} onChange={(e) => updateBenefit(i, 'icon', e.target.value)}>
              <option value="">Icon...</option>
              {icons.map((ic) => (
                <option key={ic} value={ic}>{ic}</option>
              ))}
            </select>
            <input
              type="number"
              min={0}
              max={9}
              value={b.count}
              onChange={(e) => updateBenefit(i, 'count', parseInt(e.target.value) || 0)}
            />
            <button className="remove-resource-btn" onClick={() => removeBenefit(i)}>
              x
            </button>
          </div>
        ))}
      </div>

      {/* Costs */}
      <div className="form-group">
        <div className="resource-section-header">
          <label>Costs</label>
          <div className="resource-section-options">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={showMinus}
                onChange={(e) => setShowMinus(e.target.checked)}
              />
              <span className="pm-indicator minus">-</span>
            </label>
            <button
              className="add-resource-btn"
              onClick={() => setCosts((prev) => [...prev, { icon: '', count: 1 }])}
            >
              + Add Cost
            </button>
          </div>
        </div>
        {costs.map((c, i) => (
          <div className="resource-row" key={i}>
            <select value={c.icon} onChange={(e) => updateCost(i, 'icon', e.target.value)}>
              <option value="">Icon...</option>
              {icons.map((ic) => (
                <option key={ic} value={ic}>{ic}</option>
              ))}
            </select>
            <input
              type="number"
              min={0}
              max={9}
              value={c.count}
              onChange={(e) => updateCost(i, 'count', parseInt(e.target.value) || 0)}
            />
            <button className="remove-resource-btn" onClick={() => removeCost(i)}>
              x
            </button>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="editor-actions">
        <button className="btn btn-save" disabled={saving} onClick={handleSave}>
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button className="btn btn-generate" disabled={generating} onClick={handleGenerate}>
          {generating && <span className="spinner" />}
          {generating ? 'Generating...' : 'Generate Art'}
        </button>
        {card.art_image_path && (
          <button className="btn btn-recomposite" disabled={recompositing} onClick={handleRecomposite}>
            {recompositing && <span className="spinner" />}
            {recompositing ? 'Updating...' : 'Update Card'}
          </button>
        )}
        <button className="btn btn-delete" onClick={handleDelete}>
          {confirmDelete ? 'Confirm?' : 'Delete'}
        </button>
      </div>
    </div>
  );
}
