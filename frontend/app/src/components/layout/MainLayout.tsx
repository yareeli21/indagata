/**
 * Layout principal de la aplicación
 * 
 * Incluye navegación y estructura común para todas las páginas internas
 */

import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';

export default function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('indagata_user');
    navigate('/login');
  };

  const navItems = [
    { path: '/app/instrumentos', label: 'Ver Instrumentos', icon: '📚' },
    { path: '/app/cargar', label: 'Cargar Instrumento', icon: '📤' },
    { path: '/app/chatbot', label: 'Chatbot', icon: '💬' },
    { path: '/app/kpis', label: 'KPIs', icon: '📊' },
  ];

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header con navegación */}
      <header className="bg-gray-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            {/* Logo */}
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold tracking-widest">INDAGATA</h1>
              <span className="text-xs text-gray-400 border-l border-gray-700 pl-3">
                Sistema de Gestión de Instrumentos
              </span>
            </div>

            {/* Usuario */}
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-300">
                {localStorage.getItem('indagata_user') || 'Usuario'}
              </span>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                Salir
              </button>
            </div>
          </div>

          {/* Navegación */}
          <nav className="border-t border-gray-800">
            <ul className="flex space-x-1 -mb-px">
              {navItems.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <li key={item.path}>
                    <Link
                      to={item.path}
                      className={`
                        inline-flex items-center space-x-2 px-4 py-3 border-b-2 text-sm font-medium transition-colors
                        ${
                          isActive
                            ? 'border-green-400 text-white'
                            : 'border-transparent text-gray-400 hover:text-white hover:border-gray-600'
                        }
                      `}
                    >
                      <span>{item.icon}</span>
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </div>
      </header>

      {/* Contenido principal */}
      <main>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm">
          <p>
            INDAGATA © 2026 · Gestión inteligente de instrumentos de investigación educativa
          </p>
        </div>
      </footer>
    </div>
  );
}
