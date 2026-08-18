import { useState, useEffect } from 'react';
import type { Card, Deck, Background } from '../types';
import { getComfyUIStatus, createCard, createDeck } from '../api/client';

interface Props {
  decks: Deck[];
  cards: Card[];
  backgrounds: Background[];
  selectedDeckId: string | null;
  onSelectDeck: (deckId: string | null) => void;
  onCardCreated: (newCardId: string) => void;
  onDeckCreated: () => void;
}

export default function DeckSidebar({
  decks,
  cards,
  backgrounds,
  selectedDeckId,
  onSelectDeck,
  onCardCreated,
  onDeckCreated,
}: Props) {
  const [comfyOnline, setComfyOnline] = useState<boolean | null>(null);
  const [showNewCard, setShowNewCard] = useState(false);
  const [newCardTitle, setNewCardTitle] = useState('');
  const [newCardDeckId, setNewCardDeckId] = useState('');
  const [newCardBgId, setNewCardBgId] = useState('');
  const [creating, setCreating] = useState(false);
  const [showNewDeck, setShowNewDeck] = useState(false);
  const [newDeckId, setNewDeckId] = useState('');
  const [newDeckName, setNewDeckName] = useState('');
  const [newDeckPrompt, setNewDeckPrompt] = useState('');
  const [creatingDeck, setCreatingDeck] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function check() {
      try {
        const status = await getComfyUIStatus();
        if (mounted) setComfyOnline(status.online);
      } catch {
        if (mounted) setComfyOnline(false);
      }
    }
    check();
    const interval = setInterval(check, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const cardCountByDeck = (deckId: string) => cards.filter((c) => c.deck_id === deckId).length;

  const handleCreateCard = async () => {
    if (!newCardTitle.trim() || !newCardDeckId) return;
    setCreating(true);
    try {
      const id = `sj-${Date.now().toString(36)}`;
      const card = await createCard({
        id,
        title: newCardTitle.trim(),
        deck_id: newCardDeckId,
        background_id: newCardBgId,
        benefits: {},
        costs: {},
        description: '',
        art_prompt: '',
      });
      setShowNewCard(false);
      setNewCardTitle('');
      setNewCardDeckId('');
      setNewCardBgId('');
      onCardCreated(card.id);
    } catch (err) {
      console.error('Failed to create card:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleCreateDeck = async () => {
    if (!newDeckId.trim() || !newDeckName.trim()) return;
    setCreatingDeck(true);
    try {
      const deck = await createDeck({
        id: newDeckId.trim().toLowerCase().replace(/\s+/g, '-'),
        name: newDeckName.trim(),
        back_prompt: newDeckPrompt.trim(),
      });
      setShowNewDeck(false);
      setNewDeckId('');
      setNewDeckName('');
      setNewDeckPrompt('');
      onDeckCreated();
      onSelectDeck(deck.id);
    } catch (err) {
      console.error('Failed to create deck:', err);
    } finally {
      setCreatingDeck(false);
    }
  };

  return (
    <nav className="sidebar">
      <div className="sidebar-header">CardMaker</div>
      <div className="sidebar-section-label">Manage</div>
      <ul className="deck-list">
        <li
          className={`deck-item ${selectedDeckId === '__icons__' ? 'active' : ''}`}
          onClick={() => onSelectDeck('__icons__')}
        >
          <span>Icon Editor</span>
        </li>
        <li
          className={`deck-item ${selectedDeckId === '__backgrounds__' ? 'active' : ''}`}
          onClick={() => onSelectDeck('__backgrounds__')}
        >
          <span>Background Editor</span>
        </li>
      </ul>
      <div className="sidebar-section-label">Decks</div>
      <ul className="deck-list">
        <li
          className={`deck-item ${selectedDeckId === null ? 'active' : ''}`}
          onClick={() => onSelectDeck(null)}
        >
          <span>All Cards</span>
          <span className="count">{cards.length}</span>
        </li>
        {decks.map((deck) => (
          <li
            key={deck.id}
            className={`deck-item ${selectedDeckId === deck.id ? 'active' : ''}`}
            onClick={() => onSelectDeck(deck.id)}
          >
            <span>{deck.name}</span>
            <span className="count">{cardCountByDeck(deck.id)}</span>
          </li>
        ))}
      </ul>
      <div className="sidebar-footer">
        <div className="sidebar-btn-row">
          <button className="new-card-btn" onClick={() => setShowNewCard(true)}>
            + New Card
          </button>
          <button className="new-deck-btn" onClick={() => setShowNewDeck(true)}>
            + New Deck
          </button>
        </div>
        <button
          className="export-btn"
          onClick={() => {
            const link = document.createElement('a');
            link.href = '/api/export/cards-doc';
            link.download = 'space_junk_cards.docx';
            link.click();
          }}
        >
          Export Card List
        </button>
        <div className="comfyui-status">
          <span
            className={`status-dot ${comfyOnline === true ? 'online' : 'offline'}`}
          />
          <span>ComfyUI {comfyOnline === true ? 'Online' : comfyOnline === false ? 'Offline' : 'Checking...'}</span>
        </div>
      </div>

      {showNewDeck && (
        <div className="modal-overlay" onClick={() => setShowNewDeck(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>New Deck</h2>
            <div className="form-group">
              <label>Deck ID</label>
              <input
                type="text"
                value={newDeckId}
                onChange={(e) => setNewDeckId(e.target.value)}
                placeholder="e.g. hazard"
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>Deck Name</label>
              <input
                type="text"
                value={newDeckName}
                onChange={(e) => setNewDeckName(e.target.value)}
                placeholder="e.g. Hazard Deck"
              />
            </div>
            <div className="form-group">
              <label>Back Art Prompt (optional)</label>
              <textarea
                value={newDeckPrompt}
                onChange={(e) => setNewDeckPrompt(e.target.value)}
                placeholder="Describe the deck back design..."
              />
            </div>
            <div className="modal-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setShowNewDeck(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-save"
                disabled={!newDeckId.trim() || !newDeckName.trim() || creatingDeck}
                onClick={handleCreateDeck}
              >
                {creatingDeck ? 'Creating...' : 'Create Deck'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showNewCard && (
        <div className="modal-overlay" onClick={() => setShowNewCard(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>New Card</h2>
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                value={newCardTitle}
                onChange={(e) => setNewCardTitle(e.target.value)}
                placeholder="Card title"
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>Deck</label>
              <select
                value={newCardDeckId}
                onChange={(e) => setNewCardDeckId(e.target.value)}
              >
                <option value="">Select deck...</option>
                {decks.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Background</label>
              <select
                value={newCardBgId}
                onChange={(e) => setNewCardBgId(e.target.value)}
              >
                <option value="">None</option>
                {backgrounds.map((bg) => (
                  <option key={bg.id} value={bg.id}>
                    {bg.id}
                  </option>
                ))}
              </select>
            </div>
            <div className="modal-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setShowNewCard(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-save"
                disabled={!newCardTitle.trim() || !newCardDeckId || creating}
                onClick={handleCreateCard}
              >
                {creating ? 'Creating...' : 'Create Card'}
              </button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
