import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App';
import { applyDocumentTheme, readThemePreference } from './theme/theme';

applyDocumentTheme(readThemePreference());

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
