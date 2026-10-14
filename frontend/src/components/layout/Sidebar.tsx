import React from 'react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { name: 'Executive Command Center', path: '/', enabled: true },
  { name: 'Machine Digital Twin', path: '/machine', enabled: true },
  { name: 'Energy Intelligence', path: '/energy', enabled: true },
  { name: 'Anomaly Center', path: '/anomaly', enabled: true },
  { name: 'Recommendations', path: '/recommendations', enabled: true },
  { name: 'What‑If Lab', path: '/whatif', enabled: true },
  { name: 'Impact Verification', path: '/impact', enabled: true },
  { name: 'Data Management', path: '/data', enabled: true },
  { name: 'Reports', path: '/reports', enabled: true },
  { name: 'Settings', path: '/settings', enabled: true },
];

export default function Sidebar() {
  return (
    <nav className="app-sidebar w-64 bg-gray-800 text-gray-100 flex flex-col p-4">
      <div className="text-xl font-semibold mb-6 text-teal-300">EcoTwin</div>
      <ul className="flex-1 space-y-2">
        {navItems.map(item => (
          <li key={item.name}>
            {item.enabled ? (
              <NavLink
                to={item.path}
                className={({ isActive }: { isActive: boolean }) =>
                  `block py-2 px-3 rounded hover:bg-gray-700 ${isActive ? 'bg-gray-700' : ''}`
                }
              >
                {item.name}
              </NavLink>
            ) : (
              <span className="block py-2 px-3 rounded text-gray-500 cursor-not-allowed" title="Planned">
                {item.name}
              </span>
            )}
          </li>
        ))}
      </ul>
      <div className="mt-4 text-sm text-gray-400">Version 0.2.0</div>
    </nav>
  );
}
