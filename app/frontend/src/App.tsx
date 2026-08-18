import { useState, useEffect, useCallback } from 'react';
import type { Card, Deck, Background } from './types';
import { getDecks, getCards, getBackgrounds, getIcons } from './api/client';
import DeckSidebar from './components/DeckSidebar';
import CardGallery from './components/CardGallery';
import CardEditor from './components/CardEditor';
import DeckEditor from './components/DeckEditor';
import IconEditor from './components/IconEditor';
import BackgroundEditor from './components/BackgroundEditor';
import './App.css';

function App() {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [allCards, setAllCards] = useState<Card[]>([]);
  const [backgrounds, setBackgrounds] = useState<Background[]>([]);
  const [icons, setIcons] = useState<string[]>([]);
  const [selectedDeckId, setSelectedDeckId] = useState<string | null>(null);
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);

  const fetchCards = useCallback(async () => {
    try {
      const data = await getCards();
      setAllCards(data);
    } catch (err) {
      console.error('Failed to fetch cards:', err);
    }
  }, []);

  const fetchBackgrounds = useCallback(async () => {
    try {
      const bg = await getBackgrounds();
      setBackgrounds(bg);
    } catch (err) {
      console.error('Failed to fetch backgrounds:', err);
    }
  }, []);

  useEffect(() => {
    async function init() {
      try {
        const [d, bg, ic] = await Promise.all([getDecks(), getBackgrounds(), getIcons()]);
        setDecks(d);
        setBackgrounds(bg);
        setIcons(ic);
      } catch (err) {
        console.error('Failed to load initial data:', err);
      }
    }
    init();
  }, []);

  useEffect(() => {
    // fetchCards is a stable callback; this effect just loads cards on mount
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchCards();
  }, [fetchCards]);

  // Filter cards for the gallery based on selected deck
  const displayedCards = selectedDeckId && !selectedDeckId.startsWith('__')
    ? allCards.filter((c) => c.deck_id === selectedDeckId)
    : allCards;

  const selectedCard = allCards.find((c) => c.id === selectedCardId) ?? null;

  const selectedDeck = selectedDeckId && !selectedDeckId.startsWith('__')
    ? decks.find((d) => d.id === selectedDeckId) ?? null
    : null;

  const showIconEditor = selectedDeckId === '__icons__';
  const showBackgroundEditor = selectedDeckId === '__backgrounds__';

  const handleSelectDeck = (deckId: string | null) => {
    setSelectedDeckId(deckId);
    setSelectedCardId(null);
  };

  const handleCardUpdated = useCallback(async () => {
    await fetchCards();
  }, [fetchCards]);

  const handleCardDeleted = useCallback(async () => {
    setSelectedCardId(null);
    await fetchCards();
  }, [fetchCards]);

  const handleDeckUpdated = useCallback(async () => {
    try {
      const d = await getDecks();
      setDecks(d);
    } catch (err) {
      console.error('Failed to refresh decks:', err);
    }
  }, []);

  const handleIconsChanged = useCallback(async () => {
    try {
      const ic = await getIcons();
      setIcons(ic);
    } catch (err) {
      console.error('Failed to refresh icons:', err);
    }
  }, []);

  const handleCardCreated = useCallback(
    async (newCardId: string) => {
      await fetchCards();
      setSelectedCardId(newCardId);
    },
    [fetchCards],
  );

  return (
    <div className="app-layout">
      <DeckSidebar
        decks={decks}
        cards={allCards}
        backgrounds={backgrounds}
        selectedDeckId={selectedDeckId}
        onSelectDeck={handleSelectDeck}
        onCardCreated={handleCardCreated}
        onDeckCreated={handleDeckUpdated}
      />
      <main className="main-area">
        <CardGallery
          cards={displayedCards}
          decks={decks}
          selectedCardId={selectedCardId}
          selectedDeckId={selectedDeckId}
          onSelectCard={setSelectedCardId}
        />
      </main>
      {selectedCard ? (
        <aside className="editor-panel">
          <CardEditor
            card={selectedCard}
            decks={decks}
            backgrounds={backgrounds}
            icons={icons}
            onCardUpdated={handleCardUpdated}
            onCardDeleted={handleCardDeleted}
          />
        </aside>
      ) : showIconEditor ? (
        <aside className="editor-panel">
          <IconEditor onIconsChanged={handleIconsChanged} />
        </aside>
      ) : showBackgroundEditor ? (
        <aside className="editor-panel">
          <BackgroundEditor onBackgroundsChanged={fetchBackgrounds} />
        </aside>
      ) : selectedDeck ? (
        <aside className="editor-panel">
          <DeckEditor
            deck={selectedDeck}
            onDeckUpdated={handleDeckUpdated}
          />
        </aside>
      ) : null}
    </div>
  );
}

export default App;
