/**
 * 즐겨찾기 관리 (localStorage)
 */

const STORAGE_KEY = 'mlb_watchlist';

export interface WatchlistItem {
  corp_code: string;
  corp_name: string;
  stock_code: string;
  added_at: string;
}

export function getWatchlist(): WatchlistItem[] {
  if (typeof localStorage === 'undefined') return [];
  const data = localStorage.getItem(STORAGE_KEY);
  return data ? JSON.parse(data) : [];
}

export function addToWatchlist(item: Omit<WatchlistItem, 'added_at'>): boolean {
  const list = getWatchlist();
  if (list.some(i => i.corp_code === item.corp_code)) return false;
  list.push({ ...item, added_at: new Date().toISOString() });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  return true;
}

export function removeFromWatchlist(corpCode: string): void {
  const list = getWatchlist().filter(i => i.corp_code !== corpCode);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

export function isInWatchlist(corpCode: string): boolean {
  return getWatchlist().some(i => i.corp_code === corpCode);
}
