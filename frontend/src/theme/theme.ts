export type Theme = 'dark' | 'light';

export const THEME_STORAGE_KEY = 'ecotwin-theme';

export function readThemePreference(): Theme {
  try {
    return window.localStorage.getItem(THEME_STORAGE_KEY) === 'light' ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
}

export function applyDocumentTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}
