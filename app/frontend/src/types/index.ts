export interface Card {
  id: string;
  title: string;
  deck_id: string;
  background_id: string | null;
  benefits: Record<string, number>;
  costs: Record<string, number>;
  description: string;
  art_prompt: string;
  title_size: string | null;
  desc_size: string | null;
  show_plus: boolean | null;
  show_minus: boolean | null;
  art_image_path: string | null;
  preview_image_path: string | null;
  print_image_path: string | null;
}

export interface Deck {
  id: string;
  name: string;
  back_prompt: string;
  back_image_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface CardType {
  id: string;
  name: string;
  deck_id: string;
  border_color: number[];
  border_accent: number[];
}

export interface Background {
  id: string;
  prompt: string;
  border_color: number[];
  border_accent: number[];
  has_image: boolean;
}

export interface CreateCardData {
  id: string;
  title: string;
  deck_id: string;
  background_id: string;
  benefits: Record<string, number>;
  costs: Record<string, number>;
  description: string;
  art_prompt: string;
  title_size?: string;
  desc_size?: string;
  show_plus?: boolean;
  show_minus?: boolean;
}

export interface UpdateCardData {
  title?: string;
  deck_id?: string;
  background_id?: string;
  benefits?: Record<string, number>;
  costs?: Record<string, number>;
  description?: string;
  art_prompt?: string;
  title_size?: string;
  desc_size?: string;
  show_plus?: boolean;
  show_minus?: boolean;
}

export interface ComfyUIStatus {
  online: boolean;
}
