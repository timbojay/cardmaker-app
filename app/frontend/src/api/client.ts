import type { Card, Deck, CardType, Background, CreateCardData, UpdateCardData, ComfyUIStatus } from '../types';

const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

// --- Decks ---
export function getDecks(): Promise<Deck[]> {
  return request('/decks/');
}

export function createDeck(data: { id: string; name: string; back_prompt: string }): Promise<Deck> {
  return request('/decks/', { method: 'POST', body: JSON.stringify(data) });
}

export function updateDeck(deckId: string, data: { name?: string; back_prompt?: string }): Promise<Deck> {
  return request(`/decks/${deckId}`, { method: 'PUT', body: JSON.stringify(data) });
}

export function deleteDeck(deckId: string): Promise<void> {
  return request(`/decks/${deckId}`, { method: 'DELETE' });
}

export function generateDeckBack(deckId: string): Promise<Deck> {
  return request(`/decks/${deckId}/generate-back`, { method: 'POST' });
}

export function getDeckBackUrl(deckId: string): string {
  return `/static/assets/backs/${deckId}_back.png`;
}

// --- Cards ---
export function getCards(deckId?: string): Promise<Card[]> {
  const params = new URLSearchParams();
  if (deckId) params.set('deck_id', deckId);
  const qs = params.toString();
  return request(`/cards/${qs ? `?${qs}` : ''}`);
}

export function getCard(id: string): Promise<Card> {
  return request(`/cards/${id}`);
}

export function createCard(data: CreateCardData): Promise<Card> {
  return request('/cards/', { method: 'POST', body: JSON.stringify(data) });
}

export function updateCard(id: string, data: UpdateCardData): Promise<Card> {
  return request(`/cards/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export function deleteCard(id: string): Promise<void> {
  return request(`/cards/${id}`, { method: 'DELETE' });
}

export function generateCard(id: string): Promise<Card> {
  return request(`/cards/${id}/generate`, { method: 'POST' });
}

export function recompositeCard(id: string): Promise<Card> {
  return request(`/cards/${id}/recomposite`, { method: 'POST' });
}

export function getCardPreviewUrl(id: string): string {
  return `${BASE}/cards/${id}/preview`;
}

// --- Card Types (legacy) ---
export function getCardTypes(): Promise<CardType[]> {
  return request('/card-types/');
}

// --- Backgrounds ---
export function getBackgrounds(): Promise<Background[]> {
  return request('/backgrounds/');
}

export function generateBackground(data: { id: string; prompt: string; border_color: number[]; border_accent: number[] }): Promise<Background> {
  return request('/backgrounds/generate', { method: 'POST', body: JSON.stringify(data) });
}

export function deleteBackground(id: string): Promise<void> {
  return request(`/backgrounds/${id}`, { method: 'DELETE' });
}

export function getBackgroundUrl(id: string): string {
  return `/static/assets/backgrounds/${id}_border.png`;
}

// --- Icons ---
export function getComfyUIStatus(): Promise<ComfyUIStatus> {
  return request('/comfyui/status');
}

export function getIcons(): Promise<string[]> {
  return request('/icon-names');
}

export interface IconInfo {
  id: string;
  prompt: string;
  size: string;
  size_px: number;
  has_image: boolean;
}

export function getIconList(): Promise<IconInfo[]> {
  return request('/icons/');
}

export function generateIcon(id: string, prompt: string, size: string = 'small'): Promise<IconInfo> {
  return request('/icons/generate', { method: 'POST', body: JSON.stringify({ id, prompt, size }) });
}

export function updateIcon(id: string, data: { prompt?: string; size?: string }): Promise<IconInfo> {
  return request(`/icons/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export function deleteIcon(id: string): Promise<void> {
  return request(`/icons/${id}`, { method: 'DELETE' });
}

export function getIconUrl(name: string): string {
  return `/static/assets/icons/${name}.png`;
}

export function getStaticUrl(path: string): string {
  return `/static/${path}`;
}
