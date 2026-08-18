import { useState, useEffect } from 'react';
import type { Deck } from '../types';
import { updateDeck, generateDeckBack, getDeckBackUrl } from '../api/client';

interface Props {
  deck: Deck;
  onDeckUpdated: () => void;
}

export default function DeckEditor({ deck, onDeckUpdated }: Props) {
  const [name, setName] = useState(deck.name);
  const [backPrompt, setBackPrompt] = useState(deck.back_prompt || '');
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [previewKey, setPreviewKey] = useState(0);

  useEffect(() => {
    setName(deck.name);
    setBackPrompt(deck.back_prompt || '');
    setPreviewKey((k) => k + 1);
  }, [deck]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateDeck(deck.id, { name, back_prompt: backPrompt });
      onDeckUpdated();
    } catch (err) {
      console.error('Failed to save deck:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateBack = async () => {
    setGenerating(true);
    try {
      await generateDeckBack(deck.id);
      onDeckUpdated();
      setPreviewKey((k) => k + 1);
    } catch (err) {
      console.error('Failed to generate deck back:', err);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
      <h3 className="deck-editor-title">Deck Settings</h3>

      {/* Back preview */}
      <div className="editor-preview">
        {deck.back_image_path ? (
          <img
            src={`${getDeckBackUrl(deck.id)}?v=${previewKey}`}
            alt={`${deck.name} back`}
          />
        ) : (
          <div className="editor-preview-placeholder">No deck back generated</div>
        )}
      </div>

      {/* Name */}
      <div className="form-group">
        <label>Deck Name</label>
        <input
          type="text"
          className="title-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>

      {/* Back Prompt */}
      <div className="form-group">
        <label>Back Art Prompt</label>
        <textarea
          className="tall"
          value={backPrompt}
          onChange={(e) => setBackPrompt(e.target.value)}
          placeholder="Describe the deck back design..."
        />
      </div>

      {/* Actions */}
      <div className="editor-actions">
        <button className="btn btn-save" disabled={saving} onClick={handleSave}>
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button className="btn btn-generate" disabled={generating || !backPrompt.trim()} onClick={handleGenerateBack}>
          {generating && <span className="spinner" />}
          {generating ? 'Generating...' : 'Generate Back'}
        </button>
      </div>
    </div>
  );
}
