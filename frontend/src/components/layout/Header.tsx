import React from 'react';

interface HeaderProps {
  title: string;
}

export default function Header({ title }: HeaderProps) {
  return (
    <header className="app-header bg-gray-800 text-gray-100 flex items-center h-16 px-4 shadow-md">
      <h1 className="text-2xl font-semibold">{title}</h1>
    </header>
  );
}
