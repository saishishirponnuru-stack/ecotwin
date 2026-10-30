import React from 'react';
import { Menu, X } from 'lucide-react';

interface HeaderProps {
  title: string;
  menuOpen: boolean;
  onMenuClick: () => void;
}

export default function Header({ title, menuOpen, onMenuClick }: HeaderProps) {
  return (
    <header className="app-header bg-gray-800 text-gray-100 flex items-center h-16 px-3 sm:px-4 shadow-md">
      <button
        type="button"
        className="mobile-menu-button mr-3"
        aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
        aria-expanded={menuOpen}
        aria-controls="primary-navigation"
        onClick={onMenuClick}
      >
        {menuOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
      </button>
      <div className="mobile-brand" aria-label="EcoTwin">
        <img src="/ecotwin-mark-64.png" alt="" />
        <span>EcoTwin</span>
      </div>
      <h1 className="hidden min-w-0 truncate text-base font-semibold sm:block sm:text-lg lg:text-2xl">{title}</h1>
    </header>
  );
}
