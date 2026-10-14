import { useCallback, useLayoutEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { applyDocumentTheme, readThemePreference, THEME_STORAGE_KEY } from './theme';
import type { Theme } from './theme';
import { ThemeContext } from './ThemeContext';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readThemePreference);
  const setTheme = useCallback((nextTheme: Theme) => setThemeState(nextTheme), []);

  useLayoutEffect(() => {
    applyDocumentTheme(theme);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // The current selection still applies when browser storage is unavailable.
    }
  }, [theme]);

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}
