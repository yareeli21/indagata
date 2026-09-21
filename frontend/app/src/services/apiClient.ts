/**
 * Cliente HTTP centralizado para comunicación con el backend FastAPI
 * 
 * Todas las llamadas HTTP deben pasar por este cliente.
 * Maneja configuración base, headers, interceptores y manejo de errores.
 */

import axios from 'axios';
import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

/**
 * Configuración base del cliente API
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Instancia de axios configurada
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 segundos
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Interceptor de request
 * Agrega token de autenticación si existe
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // TODO: Agregar token de autenticación cuando se implemente login
    // const token = localStorage.getItem('auth_token');
    // if (token && config.headers) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

/**
 * Interceptor de response
 * Maneja errores globales y respuestas
 */
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    // Manejo centralizado de errores
    if (error.response) {
      // El servidor respondió con un código de error
      const status = error.response.status;
      const data = error.response.data as any;
      
      switch (status) {
        case 400:
          console.error('Error de validación:', data.detail || data);
          break;
        case 401:
          console.error('No autorizado');
          // TODO: Redirigir a login cuando se implemente
          break;
        case 403:
          console.error('Acceso denegado');
          break;
        case 404:
          console.error('Recurso no encontrado');
          break;
        case 409:
          console.error('Conflicto:', data.detail || data);
          break;
        case 500:
          console.error('Error interno del servidor');
          break;
        default:
          console.error('Error desconocido:', status);
      }
    } else if (error.request) {
      // La petición se hizo pero no hubo respuesta
      console.error('Sin respuesta del servidor');
    } else {
      // Error al configurar la petición
      console.error('Error de configuración:', error.message);
    }
    
    return Promise.reject(error);
  }
);

/**
 * Función helper para extraer mensaje de error
 */
export const extractErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError;
    
    if (axiosError.response?.data) {
      const data = axiosError.response.data as any;
      return data.detail || data.message || 'Error desconocido';
    }
    
    if (axiosError.request) {
      return 'No se pudo conectar con el servidor';
    }
    
    return axiosError.message;
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'Error desconocido';
};

export default apiClient;
