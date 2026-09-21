/**
 * Página de Login (PLACEHOLDER)
 * 
 * Esta página NO está implementada funcionalmente todavía.
 * Es un placeholder para mantener la arquitectura preparada.
 * 
 * TODO: Implementar autenticación con el backend
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Simulación de login (PLACEHOLDER)
    // TODO: Implementar llamada real al backend
    setTimeout(() => {
      // Por ahora, cualquier credencial es válida
      console.log('Login simulado con:', username);
      localStorage.setItem('indagata_user', username);
      setLoading(false);
      navigate('/app/instrumentos');
    }, 800);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white tracking-widest mb-2">
            INDAGATA
          </h1>
          <div className="h-0.5 w-32 bg-green-400 mx-auto mb-6"></div>
          <p className="text-gray-400 text-sm">
            Sistema de Gestión de Instrumentos de Investigación
          </p>
        </div>

        {/* Formulario */}
        <div className="bg-gray-800 rounded-lg shadow-xl p-8 border border-gray-700">
          <h2 className="text-2xl font-semibold text-white mb-6">
            Iniciar Sesión
          </h2>

          <form onSubmit={handleLogin} className="space-y-6">
            {/* Usuario */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-2">
                Usuario
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-transparent"
                placeholder="Ingresa tu usuario"
              />
            </div>

            {/* Contraseña */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-transparent"
                placeholder="Ingresa tu contraseña"
              />
            </div>

            {/* Botón */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-green-500 hover:bg-green-600 text-gray-900 font-semibold rounded-md transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </form>

          {/* Nota de desarrollo */}
          <div className="mt-6 p-4 bg-yellow-900 bg-opacity-30 border border-yellow-700 rounded-md">
            <p className="text-yellow-200 text-xs">
              <strong>MODO DESARROLLO:</strong> Esta página es un placeholder. 
              Cualquier credencial es válida temporalmente.
            </p>
          </div>
        </div>

        {/* Link de regreso */}
        <div className="mt-6 text-center">
          <button
            onClick={() => navigate('/')}
            className="text-gray-400 hover:text-green-400 text-sm transition-colors"
          >
            ← Volver al inicio
          </button>
        </div>
      </div>
    </div>
  );
}
