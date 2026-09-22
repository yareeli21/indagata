# INDAGATA - Arquitectura Frontend

## Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Principios de Diseño](#principios-de-diseño)
3. [Estructura de Carpetas](#estructura-de-carpetas)
4. [Responsabilidades por Carpeta](#responsabilidades-por-carpeta)
5. [Flujo de Datos](#flujo-de-datos)
6. [Páginas Implementadas](#páginas-implementadas)
7. [Componentes Reutilizables](#componentes-reutilizables)
8. [Servicios y API](#servicios-y-api)
9. [Gestión de Estado](#gestión-de-estado)
10. [Tipos y Constantes](#tipos-y-constantes)
11. [Cómo Agregar Nuevas Funcionalidades](#cómo-agregar-nuevas-funcionalidades)
12. [Ejemplos Paso a Paso](#ejemplos-paso-a-paso)
13. [Mejores Prácticas](#mejores-prácticas)

---

## Visión General

INDAGATA es una aplicación React + TypeScript diseñada con **arquitectura modular tipo LEGO**, donde cada pieza es independiente y reutilizable. El sistema gestiona instrumentos de investigación educativa con un flujo ETL guiado por IA.

### Stack Tecnológico

- **React 18** - Framework UI
- **TypeScript** - Tipado estático
- **Vite** - Build tool
- **React Router v6** - Enrutamiento
- **Axios** - Cliente HTTP
- **TailwindCSS** - Estilos
- **FastAPI Backend** - API REST

### Principio Fundamental

> **Ningún componente puede llamar fetch() o axios directamente**

Toda comunicación con el backend debe pasar por el servicio centralizado.

---

## Principios de Diseño

### 1. Separación de Responsabilidades

Cada módulo tiene una responsabilidad única y bien definida:

- **Pages**: Orquestación y estado de página
- **Components**: UI reutilizable sin lógica de negocio
- **Services**: Comunicación con API
- **Types**: Contratos de datos
- **Utils**: Funciones auxiliares puras

### 2. Desacoplamiento

Los componentes NO deben:
- Conocer la estructura de la API
- Manejar llamadas HTTP directamente
- Depender de otros componentes específicos
- Contener lógica de negocio compleja

### 3. Escalabilidad

La arquitectura permite:
- Agregar nuevas páginas sin modificar código existente
- Crear nuevos componentes sin afectar los actuales
- Extender servicios sin romper funcionalidades
- Trabajar en paralelo sin conflictos

### 4. Mantenibilidad

El código debe ser:
- Autoexplicativo con nombres descriptivos
- Documentado en puntos críticos
- Consistente en estilo y patrones
- Fácil de depurar y testear

---

## Estructura de Carpetas

```
src/
├── pages/                      # Páginas principales
│   ├── LoginPage/             # Autenticación (placeholder)
│   ├── CargaInstrumentosPage/ # Wizard 5 pasos ✅ IMPLEMENTADO
│   ├── VisualizacionInstrumentosPage/ # Catálogo y detalle ✅ IMPLEMENTADO
│   ├── ChatbotPage/           # Chatbot IA (placeholder)
│   └── KpiPage/               # Dashboard KPIs (placeholder)
│
├── components/                 # Componentes reutilizables
│   ├── layout/                # Layouts y navegación
│   │   └── MainLayout.tsx    # Layout principal con header/nav
│   │
│   ├── instrumentos/          # Componentes de dominio
│   │   ├── UploadForm.tsx           # Paso 1: Subir archivo
│   │   ├── MetadataForm.tsx         # Paso 2: Metadatos DC
│   │   ├── ETLAnalysisPanel.tsx     # Paso 3: Análisis
│   │   ├── ETLProposalsPanel.tsx    # Paso 4: Propuestas
│   │   ├── IngestaPanel.tsx         # Paso 5: Ingesta
│   │   ├── SearchFilters.tsx        # Filtros de búsqueda
│   │   ├── InstrumentosTable.tsx    # Tabla de instrumentos
│   │   ├── InstrumentoDetalle.tsx   # Panel de detalle
│   │   └── DownloadButtons.tsx      # Botones de descarga
│   │
│   └── common/                # Componentes genéricos
│       ├── Stepper.tsx              # Indicador de pasos
│       ├── LoadingSpinner.tsx       # Indicador de carga
│       ├── ErrorAlert.tsx           # Alerta de error
│       └── SuccessMessage.tsx       # Mensaje de éxito
│
├── services/                   # Servicios de API
│   ├── apiClient.ts           # Cliente HTTP base
│   ├── instrumentosService.ts # Servicio de instrumentos
│   └── index.ts               # Barrel file
│
├── types/                      # Tipos TypeScript
│   ├── index.ts               # Tipos principales
│   └── constants.ts           # Constantes de dominio
│
├── routes/                     # Configuración de rutas
│   └── index.tsx              # React Router setup
│
├── utils/                      # Utilidades
│   ├── formatters.ts          # Funciones de formateo
│   └── index.ts               # Barrel file
│
├── hooks/                      # Custom hooks (futuro)
│
├── App.tsx                     # Componente raíz
├── main.tsx                    # Entry point
└── index.css                   # Estilos globales
```

---

## Responsabilidades por Carpeta

### `/pages`

**Responsabilidad**: Orquestación de componentes y gestión de estado de página.

**Contiene**:
- Llamadas a servicios
- Estado local de la página
- Lógica de flujo (wizards, navegación)
- Composición de componentes

**NO contiene**:
- Componentes UI complejos
- Lógica de negocio
- Llamadas HTTP directas

**Ejemplo**:
```typescript
// ✅ CORRECTO
const handleSubmit = async (data) => {
  const response = await instrumentosService.upload(data);
  setResult(response);
};

// ❌ INCORRECTO
const handleSubmit = async (data) => {
  const response = await axios.post('/api/upload', data);
  setResult(response.data);
};
```

### `/components`

**Responsabilidad**: UI reutilizable y presentación.

**Contiene**:
- JSX/TSX de presentación
- Props tipadas
- Estado UI local (acordeones, modales)
- Callbacks para eventos

**NO contiene**:
- Llamadas a servicios
- Lógica de negocio
- Estado global

**Ejemplo**:
```typescript
// ✅ CORRECTO
interface UploadFormProps {
  onSubmit: (data: UploadRequest) => Promise<void>;
  loading: boolean;
  error: string | null;
}

// El componente solo maneja UI y delega la acción
export default function UploadForm({ onSubmit, loading, error }: UploadFormProps) {
  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };
  // ...
}
```

### `/services`

**Responsabilidad**: Comunicación con el backend.

**Contiene**:
- Métodos de API mapeados 1:1 con endpoints
- Transformación de requests/responses
- Manejo de errores HTTP
- Tipos de entrada/salida

**NO contiene**:
- Componentes React
- Estado de UI
- Lógica de presentación

**Ejemplo**:
```typescript
// ✅ CORRECTO - Un método por endpoint
class InstrumentosService {
  async upload(request: UploadWithFileRequest): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('archivo', request.file);
    const response = await apiClient.post('/instrumentos/upload', formData);
    return response.data;
  }
}
```

### `/types`

**Responsabilidad**: Contratos de datos y constantes.

**Contiene**:
- Interfaces TypeScript
- Types y Enums
- Constantes de dominio
- Mapeos de valores

**NO contiene**:
- Lógica
- Componentes
- Funciones (excepto type guards)

### `/utils`

**Responsabilidad**: Funciones auxiliares puras.

**Contiene**:
- Formateadores
- Validadores
- Transformadores
- Helpers

**NO contiene**:
- Estado
- Side effects
- Componentes

---

## Flujo de Datos

### Arquitectura de Comunicación

```
┌─────────────┐
│   Usuario   │
└──────┬──────┘
       │ Interacción
       ▼
┌─────────────────┐
│  Componente UI  │ ← Solo presenta y captura eventos
└──────┬──────────┘
       │ Callback
       ▼
┌─────────────────┐
│     Página      │ ← Orquesta y maneja estado
└──────┬──────────┘
       │ Llamada
       ▼
┌─────────────────┐
│    Servicio     │ ← Comunica con API
└──────┬──────────┘
       │ HTTP
       ▼
┌─────────────────┐
│  Backend API    │
└─────────────────┘
```

### Ejemplo Completo del Flujo

```typescript
// 1. COMPONENTE - UploadForm.tsx
export default function UploadForm({ onSubmit }: Props) {
  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({ file, tipo_instrumento, visibilidad });
  };
  
  return <form onSubmit={handleSubmit}>...</form>;
}

// 2. PÁGINA - CargaInstrumentosPage.tsx
export default function CargaInstrumentosPage() {
  const handleUpload = async (request: UploadWithFileRequest) => {
    const response = await instrumentosService.upload(request);
    setInstrumentoId(response.instrumento_id);
  };
  
  return <UploadForm onSubmit={handleUpload} />;
}

// 3. SERVICIO - instrumentosService.ts
class InstrumentosService {
  async upload(request: UploadWithFileRequest): Promise<UploadResponse> {
    const response = await apiClient.post('/instrumentos/upload', formData);
    return response.data;
  }
}

// 4. BACKEND - routers_cargar_instru.py
@router.post("/upload")
async def upload_instrumento(...) -> UploadResponse:
    return UploadResponse(instrumento_id=..., estado="pendiente")
```

---

## Páginas Implementadas

### 1. LoginPage (Placeholder)

**Ruta**: `/login`

**Estado**: Placeholder funcional

**Funcionalidad Actual**:
- Acepta cualquier credencial
- Redirige a `/instrumentos`
- Guarda sesión en localStorage

**TODO para producción**:
- Implementar autenticación real
- Conectar con endpoint `/auth/login`
- Manejar tokens JWT
- Implementar refresh tokens

### 2. CargaInstrumentosPage ✅

**Ruta**: `/cargar`

**Estado**: Completamente implementado

**Funcionalidad**:
- Wizard de 5 pasos controlado por estados
- Paso 1: Upload archivo
- Paso 2: Metadatos Dublin Core (13 campos)
- Paso 3: Análisis ETL con IA
- Paso 4: Revisión de propuestas
- Paso 5: Ingesta final

**Características**:
- Navegación condicional por estados del backend
- Stepper visual de progreso
- Manejo de errores por paso
- Validación de formularios
- Carga asíncrona con indicadores

**Endpoints utilizados**:
```
POST   /instrumentos/upload
POST   /instrumentos/metadata
GET    /instrumentos/{id}/etl/extract
GET    /instrumentos/{id}/etl/proposals
POST   /instrumentos/{id}/etl/approve
POST   /instrumentos/ingesta
```

### 3. VisualizacionInstrumentosPage ✅

**Ruta**: `/instrumentos`

**Estado**: Completamente implementado

**Funcionalidad**:
- Catálogo filtrable de instrumentos
- Panel de detalle completo
- Filtros: tipo, idioma, KPI
- Descarga de archivos
- Resumen estadístico

**Layout**:
- Área 1 (2/3): Filtros + Tabla
- Área 2 (1/3): Detalle (sticky)

**Endpoints utilizados**:
```
GET    /instrumentos
GET    /instrumentos/{id}
GET    /instrumentos/{id}/download?type={original|json|sav}
```

### 4. ChatbotPage (Placeholder)

**Ruta**: `/chatbot`

**Estado**: Placeholder

**Funcionalidad Planificada**:
- Chat con IA usando RAG
- Consultas sobre instrumentos
- Búsqueda semántica
- Análisis de KPIs

### 5. KpiPage (Placeholder)

**Ruta**: `/kpis`

**Estado**: Placeholder

**Funcionalidad Planificada**:
- Dashboard de métricas
- Gráficos interactivos
- Filtros temporales
- Exportación de reportes

---

## Componentes Reutilizables

### Componentes de Carga (`/components/instrumentos`)

#### UploadForm
**Propósito**: Subir archivo del instrumento

**Props**:
```typescript
interface UploadFormProps {
  onSubmit: (request: UploadWithFileRequest) => Promise<void>;
  loading: boolean;
  error: string | null;
}
```

**Uso**:
```typescript
<UploadForm
  onSubmit={handleUpload}
  loading={loading}
  error={error}
/>
```

#### MetadataForm
**Propósito**: Formulario de 13 campos Dublin Core

**Props**:
```typescript
interface MetadataFormProps {
  instrumentoId: number;
  onSubmit: (request: MetadataRequest) => Promise<void>;
  loading: boolean;
  error: string | null;
}
```

#### ETLProposalsPanel
**Propósito**: Revisar y aprobar propuestas ETL

**Props**:
```typescript
interface ETLProposalsPanelProps {
  instrumentoId: number;
  propuestas: EtlPropuestaOutput[];
  onApprove: (request: AprobacionRequest) => Promise<void>;
  loading: boolean;
  error: string | null;
}
```

### Componentes de Visualización

#### InstrumentosTable
**Propósito**: Tabla de instrumentos con selección

**Props**:
```typescript
interface InstrumentosTableProps {
  instrumentos: InstrumentoResumen[];
  selectedId: number | null;
  onSelect: (instrumento: InstrumentoResumen) => void;
  loading: boolean;
}
```

#### InstrumentoDetalle
**Propósito**: Panel de detalle completo

**Props**:
```typescript
interface InstrumentoDetalleProps {
  instrumento: InstrumentoDetalle | null;
  loading: boolean;
}
```

### Componentes Comunes (`/components/common`)

Componentes genéricos reutilizables en toda la aplicación:

- **Stepper**: Indicador de pasos de wizard
- **LoadingSpinner**: Indicador de carga
- **ErrorAlert**: Alerta de error con cierre
- **SuccessMessage**: Mensaje de éxito

---

## Servicios y API

### InstrumentosService

**Ubicación**: `src/services/instrumentosService.ts`

**Métodos Disponibles**:

```typescript
class InstrumentosService {
  // PASO 1: Subir archivo
  async upload(request: UploadWithFileRequest): Promise<UploadResponse>
  
  // PASO 2: Registrar metadatos
  async createMetadata(request: MetadataRequest): Promise<MetadataResponse>
  
  // PASO 3: Analizar ETL
  async extractETL(instrumentoId: number): Promise<EtlExtractResponse>
  
  // PASO 4: Obtener propuestas
  async getProposals(instrumentoId: number): Promise<EtlProposalsResponse>
  
  // PASO 4: Aprobar propuestas
  async approveProposals(
    instrumentoId: number,
    request: AprobacionRequest
  ): Promise<AprobacionResponse>
  
  // PASO 5: Ejecutar ingesta
  async ingest(request: IngestaRequest): Promise<IngestaResponse>
  
  // Listar instrumentos
  async list(filtros?: FiltrosInstrumento): Promise<InstrumentoResumen[]>
  
  // Obtener detalle
  async getDetail(instrumentoId: number): Promise<InstrumentoDetalle>
  
  // Descargar archivo
  async download(instrumentoId: number, tipo: TipoDescarga): Promise<Blob>
  async downloadFile(
    instrumentoId: number,
    tipo: TipoDescarga,
    nombreArchivo: string
  ): Promise<void>
  
  // Eliminar instrumento
  async deleteInstrumento(instrumentoId: number): Promise<EliminacionResponse>
}
```

**Uso**:
```typescript
import { instrumentosService } from '@/services';

const response = await instrumentosService.upload(request);
```

---

## Gestión de Estado

### Estrategia Actual

La aplicación utiliza **React State local** con `useState` y `useEffect`.

**Razones**:
- Simplicidad
- Claridad para desarrolladores académicos
- Sin dependencias adicionales
- Suficiente para el alcance actual

### Patrón de Estado en Páginas

```typescript
export default function MiPagina() {
  // Estado de datos
  const [data, setData] = useState<DataType[]>([]);
  
  // Estados de UI
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Cargar datos
  const cargarDatos = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await miServicio.getData();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    cargarDatos();
  }, []);
  
  return <MiComponente data={data} loading={loading} error={error} />;
}
```

### Migración Futura

Si la aplicación crece, considerar:
- **Zustand** para estado global simple
- **React Query** para estado de servidor
- **Context API** para temas/configuración

---

## Tipos y Constantes

### Tipos Principales (`/types/index.ts`)

Los tipos mapean 1:1 los schemas Pydantic del backend:

```typescript
// Tipos base
export type TipoInstrumento = "encuesta" | "entrevista" | "prueba_estandarizada";
export type EstadoPipeline = "pendiente" | "metadata_registrado" | ...;

// Schemas de entrada
export interface UploadRequest { ... }
export interface MetadataRequest { ... }
export interface AprobacionRequest { ... }

// Schemas de salida
export interface InstrumentoDetalle { ... }
export interface EtlPropuestaOutput { ... }
```

### Constantes (`/types/constants.ts`)

```typescript
// Labels legibles
export const TIPO_INSTRUMENTO_LABELS = {
  encuesta: "Encuesta",
  entrevista: "Entrevista",
  prueba_estandarizada: "Prueba Estandarizada"
};

// Mapeo de estados a pasos del wizard
export const ESTADO_TO_WIZARD = {
  pendiente: { currentStep: 1, enabledSteps: [1, 2] },
  metadata_registrado: { currentStep: 3, enabledSteps: [3] },
  // ...
};
```

---

## Cómo Agregar Nuevas Funcionalidades

### Checklist General

Cuando se agrega una nueva funcionalidad, seguir estos pasos:

1. ✅ **Definir tipos** en `/types`
2. ✅ **Crear servicio** (si requiere API) en `/services`
3. ✅ **Crear componentes** reutilizables en `/components`
4. ✅ **Crear página** en `/pages`
5. ✅ **Registrar ruta** en `/routes`
6. ✅ **Actualizar navegación** en `MainLayout`
7. ✅ **Documentar** en este archivo

### Flujo Detallado

#### 1. Agregar un Nuevo Endpoint

**Archivo**: `src/services/instrumentosService.ts`

```typescript
// 1. Agregar método al servicio
async miNuevoEndpoint(parametro: number): Promise<MiResponse> {
  try {
    const response = await apiClient.get(`/mi-ruta/${parametro}`);
    return response.data;
  } catch (error) {
    const message = extractErrorMessage(error);
    throw new Error(`Error en operación: ${message}`);
  }
}
```

#### 2. Crear un Nuevo Componente

**Archivo**: `src/components/dominio/MiComponente.tsx`

```typescript
/**
 * Componente MiComponente - Descripción breve
 * 
 * Explicación de qué hace y cuándo usarlo
 */

interface MiComponenteProps {
  data: MiTipo;
  onAction: (id: number) => void;
  loading: boolean;
}

export default function MiComponente({ data, onAction, loading }: MiComponenteProps) {
  if (loading) {
    return <LoadingSpinner />;
  }
  
  return (
    <div>
      {/* UI aquí */}
      <button onClick={() => onAction(data.id)}>
        Acción
      </button>
    </div>
  );
}
```

#### 3. Crear una Nueva Página

**Archivo**: `src/pages/MiNuevaPagina/MiNuevaPagina.tsx`

```typescript
/**
 * Página MiNuevaPagina
 * 
 * Descripción de la funcionalidad
 */

import { useState, useEffect } from 'react';
import { miServicio } from '@/services';
import MiComponente from '@/components/dominio/MiComponente';

export default function MiNuevaPagina() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const cargarDatos = async () => {
    setLoading(true);
    try {
      const result = await miServicio.getData();
      setData(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    cargarDatos();
  }, []);
  
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1>Mi Nueva Página</h1>
      <MiComponente data={data} loading={loading} />
    </div>
  );
}
```

**Archivo**: `src/pages/MiNuevaPagina/index.ts`

```typescript
export { default } from './MiNuevaPagina';
```

#### 4. Registrar la Ruta

**Archivo**: `src/routes/index.tsx`

```typescript
import MiNuevaPagina from '../pages/MiNuevaPagina';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <ProtectedRoute><MainLayout /></ProtectedRoute>,
    children: [
      // ... rutas existentes
      {
        path: 'mi-ruta',
        element: <MiNuevaPagina />,
      },
    ],
  },
]);
```

#### 5. Agregar a la Navegación

**Archivo**: `src/components/layout/MainLayout.tsx`

```typescript
const navItems = [
  // ... items existentes
  { path: '/mi-ruta', label: 'Mi Página', icon: '🎯' },
];
```

---

## Ejemplos Paso a Paso

### Ejemplo 1: Implementar Página de Chatbot

#### Paso 1: Crear Tipos

**Archivo**: `src/types/index.ts`

```typescript
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatRequest {
  message: string;
  instrumento_id?: number;
}

export interface ChatResponse {
  message: string;
  sources?: string[];
}
```

#### Paso 2: Crear Servicio

**Archivo**: `src/services/chatService.ts`

```typescript
import apiClient, { extractErrorMessage } from './apiClient';
import type { ChatRequest, ChatResponse } from '../types';

class ChatService {
  private readonly basePath = '/chat';

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await apiClient.post<ChatResponse>(
        `${this.basePath}/message`,
        request
      );
      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al enviar mensaje: ${message}`);
    }
  }
}

export const chatService = new ChatService();
export default ChatService;
```

**Actualizar**: `src/services/index.ts`

```typescript
export { chatService } from './chatService';
```

#### Paso 3: Crear Componentes

**Archivo**: `src/components/chat/ChatMessage.tsx`

```typescript
import type { ChatMessage } from '../../types';

interface ChatMessageProps {
  message: ChatMessage;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[70%] rounded-lg p-4 ${
          isUser ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-900'
        }`}
      >
        <p className="text-sm">{message.content}</p>
      </div>
    </div>
  );
}
```

**Archivo**: `src/components/chat/ChatInput.tsx`

```typescript
import { useState } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      onSend(message);
      setMessage('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex space-x-2">
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        disabled={disabled}
        placeholder="Escribe tu pregunta..."
        className="flex-1 px-4 py-2 border rounded-lg"
      />
      <button
        type="submit"
        disabled={disabled || !message.trim()}
        className="px-6 py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50"
      >
        Enviar
      </button>
    </form>
  );
}
```

#### Paso 4: Implementar Página

**Archivo**: `src/pages/ChatbotPage/ChatbotPage.tsx`

```typescript
import { useState } from 'react';
import { chatService } from '../../services';
import type { ChatMessage } from '../../types';
import ChatMessage from '../../components/chat/ChatMessage';
import ChatInput from '../../components/chat/ChatInput';

export default function ChatbotPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSendMessage = async (content: string) => {
    // Agregar mensaje del usuario
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await chatService.sendMessage({ message: content });
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toISOString(),
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Chatbot con IA</h1>
        
        <div className="bg-white rounded-lg shadow p-6 h-[600px] flex flex-col">
          {/* Mensajes */}
          <div className="flex-1 overflow-y-auto space-y-4 mb-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
          </div>
          
          {/* Input */}
          <ChatInput onSend={handleSendMessage} disabled={loading} />
        </div>
      </div>
    </div>
  );
}
```

#### Paso 5: Registrar Ruta

Ya está registrada en `/routes/index.tsx` como placeholder. Solo reemplazar la implementación.

---

### Ejemplo 2: Agregar Eliminación de Instrumentos

#### Paso 1: El servicio ya existe

```typescript
// Ya implementado en instrumentosService.ts
async deleteInstrumento(instrumentoId: number): Promise<EliminacionResponse>
```

#### Paso 2: Agregar botón en InstrumentoDetalle

**Actualizar**: `src/components/instrumentos/InstrumentoDetalle.tsx`

```typescript
interface InstrumentoDetalleProps {
  instrumento: InstrumentoDetalle | null;
  loading: boolean;
  onDelete?: (id: number) => void; // Nueva prop
}

export default function InstrumentoDetalle({ 
  instrumento, 
  loading,
  onDelete 
}: InstrumentoDetalleProps) {
  // ... código existente
  
  return (
    <div className="space-y-6">
      {/* ... contenido existente ... */}
      
      {/* Botón de eliminación */}
      {onDelete && (
        <button
          onClick={() => onDelete(instrumento!.instrumento_id)}
          className="w-full px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-md"
        >
          Eliminar Instrumento
        </button>
      )}
    </div>
  );
}
```

#### Paso 3: Implementar en la página

**Actualizar**: `src/pages/VisualizacionInstrumentosPage/VisualizacionInstrumentosPage.tsx`

```typescript
const handleDelete = async (id: number) => {
  if (!confirm('¿Estás seguro de eliminar este instrumento?')) {
    return;
  }
  
  try {
    await instrumentosService.deleteInstrumento(id);
    // Recargar lista
    cargarInstrumentos();
    // Limpiar selección
    setSelectedInstrumento(null);
    setInstrumentoDetalle(null);
  } catch (error) {
    setErrorDetalle(error instanceof Error ? error.message : 'Error al eliminar');
  }
};

// En el render
<InstrumentoDetalleComponent
  instrumento={instrumentoDetalle}
  loading={loadingDetalle}
  onDelete={handleDelete}
/>
```

---

## Mejores Prácticas

### 1. Nombrado de Archivos

- **Componentes**: PascalCase (`MiComponente.tsx`)
- **Servicios**: camelCase (`miServicio.ts`)
- **Tipos**: camelCase (`index.ts`, `constants.ts`)
- **Páginas**: PascalCase (`MiPagina.tsx`)

### 2. Estructura de Componentes

```typescript
/**
 * Docstring del componente
 */

import { ... } from 'react';
import type { ... } from '../types';

// Props interface
interface MiComponenteProps {
  prop1: string;
  prop2: number;
}

// Componente
export default function MiComponente({ prop1, prop2 }: MiComponenteProps) {
  // 1. State
  const [state, setState] = useState();
  
  // 2. Effects
  useEffect(() => {
    // ...
  }, []);
  
  // 3. Handlers
  const handleAction = () => {
    // ...
  };
  
  // 4. Early returns
  if (loading) return <LoadingSpinner />;
  
  // 5. Render
  return (
    <div>
      {/* JSX */}
    </div>
  );
}
```

### 3. Manejo de Errores

```typescript
// ✅ CORRECTO
try {
  const result = await service.getData();
  setData(result);
} catch (err) {
  setError(err instanceof Error ? err.message : 'Error desconocido');
}

// ❌ INCORRECTO
try {
  const result = await service.getData();
  setData(result);
} catch (err) {
  setError(err.message); // err puede no ser Error
}
```

### 4. Tipos vs Interfaces

```typescript
// Para props de componentes: usar interface
interface MiComponenteProps {
  titulo: string;
}

// Para uniones y aliases: usar type
type TipoInstrumento = "encuesta" | "entrevista";
type Estado = { data: Data } | { error: string };
```

### 5. Imports

```typescript
// Orden de imports:
// 1. React
import { useState, useEffect } from 'react';

// 2. Librerías externas
import { useNavigate } from 'react-router-dom';

// 3. Servicios
import { instrumentosService } from '../../services';

// 4. Tipos
import type { MiTipo } from '../../types';

// 5. Componentes
import MiComponente from '../../components/MiComponente';

// 6. Utilidades
import { formatDate } from '../../utils';
```

### 6. CSS y Estilos

```typescript
// ✅ Usar TailwindCSS
<div className="flex items-center space-x-4">

// ✅ Condicionales con template literals
<div className={`px-4 py-2 ${active ? 'bg-blue-500' : 'bg-gray-200'}`}>

// ❌ Evitar estilos inline
<div style={{ padding: '16px' }}>
```

### 7. Accesibilidad

```typescript
// ✅ Labels en formularios
<label htmlFor="email">Email</label>
<input id="email" type="email" />

// ✅ Botones con texto descriptivo
<button>Guardar instrumento</button>

// ✅ Alt text en imágenes
<img src="..." alt="Descripción de la imagen" />
```

---

## Conclusión

Esta arquitectura está diseñada para:

1. **Facilitar el desarrollo colaborativo** entre múltiples desarrolladores
2. **Permitir extensibilidad** sin modificar código existente
3. **Mantener claridad** para desarrolladores académicos
4. **Escalar** cuando sea necesario

**Regla de Oro**: Si tienes dudas, busca un componente similar ya implementado y sigue el mismo patrón.

---

## Contacto y Soporte

Para dudas sobre la arquitectura:
1. Revisar este documento
2. Revisar código existente similar
3. Consultar con el arquitecto del proyecto

**Última actualización**: Septiembre 2026