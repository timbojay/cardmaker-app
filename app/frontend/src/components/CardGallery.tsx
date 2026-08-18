import { useState } from 'react';
import type { Card, Deck } from '../types';
import { getCardPreviewUrl } from '../api/client';

interface Props {
  cards: Card[];
  decks: Deck[];
  selectedCardId: string | null;
  selectedDeckId: string | null;
  onSelectCard: (id: string) => void;
}

export default function CardGallery({ cards, decks, selectedCardId, selectedDeckId, onSelectCard }: Props) {
  const [filterDeckId, setFilterDeckId] = useState<string | null>(null);
  const isAllView = selectedDeckId === null;

  const filteredCards = isAllView && filterDeckId
    ? cards.filter((c) => c.deck_id === filterDeckId)
    : cards;

  if (cards.length === 0) {
    return (
      <div className="empty-state">
        <p>No cards yet. Click "+ New Card" to get started.</p>
      </div>
    );
  }

  return (
    <>
      <div className="gallery-header-row">
        <h1 className="gallery-header">Cards ({filteredCards.length})</h1>
        {isAllView && decks.length > 1 && (
          <div className="gallery-deck-filter">
            <button
              className={`filter-btn${filterDeckId === null ? ' filter-btn-active' : ''}`}
              onClick={() => setFilterDeckId(null)}
            >
              All
            </button>
            {decks.map((d) => (
              <button
                key={d.id}
                className={`filter-btn${filterDeckId === d.id ? ' filter-btn-active' : ''}`}
                onClick={() => setFilterDeckId(d.id)}
              >
                {d.name}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="card-grid">
        {filteredCards.map((card) => (
          <div
            key={card.id}
            className={`card-thumb ${selectedCardId === card.id ? 'selected' : ''}`}
            onClick={() => onSelectCard(card.id)}
          >
{card.preview_image_path ? (
  <img
    className="card-thumb-image"
    src={getCardPreviewUrl(card.id)}
    alt={card.title}
    loading="lazy"
  />
) : (
  <div className="card-thumb-placeholder">Art Placeholder</div>
)}
            <div className="card-thumb-title">{card.title}</div>
            <div className="card-thumb-meta">{card.id}</div>
          </div>
        ))}
      </div>
    </>
  );
}
