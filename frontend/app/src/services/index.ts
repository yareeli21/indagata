/**
 * Barrel file para servicios
 * 
 * Facilita las importaciones desde otros módulos:
 * import { instrumentosService } from '@/services';
 */

export { instrumentosService, default as InstrumentosService } from './instrumentosService';
export { default as apiClient, extractErrorMessage } from './apiClient';
