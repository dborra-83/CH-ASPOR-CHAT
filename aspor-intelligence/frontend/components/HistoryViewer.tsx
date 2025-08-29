import React, { useState, useEffect } from 'react';
import { 
  IconHistory, 
  IconFile, 
  IconCalendar,
  IconEye,
  IconAlertCircle,
  IconCheck,
  IconClock,
  IconChevronDown,
  IconChevronUp,
  IconLoader,
  IconCopy,
  IconBrain,
  IconFileText,
  IconDownload,
  IconExternalLink,
  IconSearch,
  IconFilter,
  IconX,
  IconRefresh
} from '@tabler/icons-react';
import axios from 'axios';
import AnalysisFormatter from './AnalysisFormatter';

interface HistoryItem {
  runId: string;
  status: string;
  model?: string;
  fileName: string;
  textExtracted: string;
  processedAt: string;
  completedAt?: string;
  errorMessage?: string;
  analysis?: string;
  analysisResult?: string;  // New field from async processing
  bedrockResult?: string;  // Legacy field
  analysisKey?: string;
  fileSize?: number;
  extractedLength?: number;
  analysisMethod?: string;  // Track how it was analyzed
}

interface HistoryViewerProps {
  userId: string;
  apiUrl: string;
  onViewResult: (runId: string) => void;
}

export default function HistoryViewer({ 
  userId, 
  apiUrl,
  onViewResult 
}: HistoryViewerProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [loadingAnalysis, setLoadingAnalysis] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterModel, setFilterModel] = useState<string>('all');

  // Helper function to format dates in local timezone
  const formatLocalDateTime = (dateString: string | undefined, format: 'short' | 'long' = 'short') => {
    if (!dateString) return 'No disponible';
    
    const date = new Date(dateString);
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    if (format === 'long') {
      return date.toLocaleString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZone: userTimezone,
        timeZoneName: 'short'
      });
    } else {
      return date.toLocaleString('es-ES', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone: userTimezone
      });
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [userId]);

  const toggleAnalysis = async (runId: string) => {
    console.log('Toggle analysis for:', runId);
    
    if (expandedItems.has(runId)) {
      // Collapse if already expanded
      const newExpanded = new Set(expandedItems);
      newExpanded.delete(runId);
      setExpandedItems(newExpanded);
    } else {
      // Expand and load analysis if needed
      const item = history.find(h => h.runId === runId);
      console.log('Item found:', item);
      console.log('Has analysis:', item?.analysis);
      console.log('Has bedrockResult:', item?.bedrockResult);
      
      // Check if we already have the analysis (from any field)
      const hasAnalysis = item?.analysis || item?.analysisResult || item?.bedrockResult;
      if (item && !hasAnalysis) {
        console.log('Loading analysis from API for:', runId);
        // Only load from API if we don't have the analysis yet
        const newLoading = new Set(loadingAnalysis);
        newLoading.add(runId);
        setLoadingAnalysis(newLoading);
        
        try {
          const baseUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
          // Try new status endpoint first
          let response;
          try {
            const statusUrl = `${baseUrl}/status/${runId}`;
            console.log('Fetching from status endpoint:', statusUrl);
            response = await axios.get(statusUrl);
          } catch (err) {
            // Fallback to old endpoint
            const url = `${baseUrl}/runs/${runId}`;
            console.log('Fallback to runs endpoint:', url);
            response = await axios.get(url);
          }
          
          console.log('API Response:', response.data);
          
          // Update history with analysis - check all possible fields
          const analysisContent = response.data.analysis || 
                                 response.data.analysisResult || 
                                 response.data.bedrockResult || 
                                 null;
          
          const updatedHistory = history.map(h => 
            h.runId === runId ? { 
              ...h, 
              analysis: analysisContent,
              analysisResult: response.data.analysisResult,
              bedrockResult: response.data.bedrockResult,
              model: response.data.model || h.model
            } : h
          );
          setHistory(updatedHistory);
        } catch (err: any) {
          console.error('Error loading analysis:', err);
          console.error('Error details:', err.response?.data);
        } finally {
          const newLoading = new Set(loadingAnalysis);
          newLoading.delete(runId);
          setLoadingAnalysis(newLoading);
        }
      } else {
        console.log('Analysis already available, expanding view');
      }
      
      const newExpanded = new Set(expandedItems);
      newExpanded.add(runId);
      setExpandedItems(newExpanded);
    }
  };

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const baseUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
      const url = `${baseUrl}/history/${userId}`;
      console.log('Fetching history from:', url);
      const response = await axios.get(url);
      console.log('History response:', response.data);
      
      // Log each item to see what data we're receiving
      if (response.data.history) {
        response.data.history.forEach((item: any, index: number) => {
          console.log(`History item ${index}:`, {
            runId: item.runId,
            status: item.status,
            hasAnalysis: !!item.analysis,
            hasBedrockResult: !!item.bedrockResult,
            analysisLength: item.analysis?.length || 0,
            bedrockResultLength: item.bedrockResult?.length || 0
          });
        });
      }
      
      setHistory(response.data.history || []);
      setError(null);
    } catch (err: any) {
      setError('Error al cargar el historial');
      console.error('Error fetching history:', err);
      console.error('Error details:', err.response?.data);
      // If CORS error or network error, try to provide more specific message
      if (err.code === 'ERR_NETWORK') {
        setError('Error de red. Verifique la conexión y los permisos CORS.');
      }
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <IconCheck size={16} className="text-green-600" />;
      case 'FAILED':
        return <IconAlertCircle size={16} className="text-red-600" />;
      default:
        return <IconClock size={16} className="text-yellow-600" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium inline-flex items-center';
      case 'FAILED':
        return 'bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium inline-flex items-center';
      default:
        return 'bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium inline-flex items-center';
    }
  };

  const getModelName = (model?: string) => {
    if (model === 'A') return 'Contragarantías';
    if (model === 'B') return 'Informes Sociales';
    return 'N/A';
  };

  // Filter history based on search and filters
  const filteredHistory = history.filter(item => {
    const matchesSearch = searchTerm === '' || 
      item.fileName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.runId.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = filterStatus === 'all' || item.status === filterStatus;
    const matchesModel = filterModel === 'all' || item.model === filterModel;
    
    return matchesSearch && matchesStatus && matchesModel;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <IconHistory size={48} className="mx-auto mb-4 text-gray-400 animate-pulse" />
          <p className="text-gray-600">Cargando historial...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <IconAlertCircle size={48} className="mx-auto mb-4 text-red-400" />
          <p className="text-red-600">{error}</p>
          <button 
            onClick={fetchHistory}
            className="tabler-btn-primary mt-4"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <IconHistory size={48} className="mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600">No hay historial disponible</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gradient-to-br from-gray-50 to-white min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-2xl font-bold text-gray-900 flex items-center">
                <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg mr-3">
                  <IconHistory size={28} className="text-white" />
                </div>
                Historial de Análisis
              </h3>
              <p className="text-sm text-gray-600 mt-2 ml-14">
                {history.length} documento{history.length !== 1 ? 's' : ''} • 
                {filteredHistory.length} visible{filteredHistory.length !== 1 ? 's' : ''} • 
                {Intl.DateTimeFormat().resolvedOptions().timeZone}
              </p>
            </div>
            <button 
              onClick={fetchHistory}
              className="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-200 flex items-center space-x-2 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
            >
              <IconRefresh size={18} />
              <span className="font-medium">Actualizar</span>
            </button>
          </div>

          {/* Search and Filter Bar */}
          <div className="bg-white p-4 rounded-xl shadow-md border border-gray-100">
            <div className="flex flex-col lg:flex-row gap-4">
              {/* Search Input */}
              <div className="flex-1">
                <div className="relative">
                  <IconSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    type="text"
                    placeholder="Buscar por nombre de archivo o ID..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-10 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                  />
                  {searchTerm && (
                    <button
                      onClick={() => setSearchTerm('')}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      <IconX size={18} />
                    </button>
                  )}
                </div>
              </div>

              {/* Status Filter */}
              <div className="flex items-center space-x-2">
                <IconFilter size={20} className="text-gray-500" />
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all bg-white"
                >
                  <option value="all">Todos los estados</option>
                  <option value="COMPLETED">Completados</option>
                  <option value="FAILED">Fallidos</option>
                  <option value="PROCESSING">En proceso</option>
                </select>
              </div>

              {/* Model Filter */}
              <div className="flex items-center space-x-2">
                <IconBrain size={20} className="text-gray-500" />
                <select
                  value={filterModel}
                  onChange={(e) => setFilterModel(e.target.value)}
                  className="px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all bg-white"
                >
                  <option value="all">Todos los modelos</option>
                  <option value="A">Contragarantías</option>
                  <option value="B">Informes Sociales</option>
                </select>
              </div>
            </div>

            {/* Active Filters Display */}
            {(searchTerm || filterStatus !== 'all' || filterModel !== 'all') && (
              <div className="mt-3 flex items-center space-x-2">
                <span className="text-sm text-gray-500">Filtros activos:</span>
                {searchTerm && (
                  <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                    Búsqueda: {searchTerm}
                  </span>
                )}
                {filterStatus !== 'all' && (
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                    Estado: {filterStatus}
                  </span>
                )}
                {filterModel !== 'all' && (
                  <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                    Modelo: {getModelName(filterModel)}
                  </span>
                )}
                <button
                  onClick={() => {
                    setSearchTerm('');
                    setFilterStatus('all');
                    setFilterModel('all');
                  }}
                  className="text-xs text-gray-500 hover:text-gray-700 underline"
                >
                  Limpiar filtros
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Results Section */}
        {filteredHistory.length === 0 ? (
          <div className="bg-white rounded-xl p-12 text-center shadow-sm border border-gray-100">
            <IconSearch size={48} className="mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500 text-lg mb-2">
              {searchTerm || filterStatus !== 'all' || filterModel !== 'all' 
                ? 'No se encontraron resultados con los filtros aplicados'
                : 'No hay documentos procesados aún'}
            </p>
            {(searchTerm || filterStatus !== 'all' || filterModel !== 'all') && (
              <button
                onClick={() => {
                  setSearchTerm('');
                  setFilterStatus('all');
                  setFilterModel('all');
                }}
                className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Limpiar filtros
              </button>
            )}
          </div>
        ) : (
          <div className="grid gap-4">
            {filteredHistory.map((item) => (
              <div 
                key={item.runId}
                className="bg-white border border-gray-100 rounded-xl shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden group"
              >
                {/* Status Color Bar */}
                <div className={`h-1 ${item.status === 'COMPLETED' ? 'bg-gradient-to-r from-green-400 to-emerald-500' : item.status === 'FAILED' ? 'bg-gradient-to-r from-red-400 to-pink-500' : 'bg-gradient-to-r from-yellow-400 to-orange-500'}`} />
                
                <div className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start space-x-3">
                <div className="p-2 bg-blue-50 rounded-lg">
                  <IconFile size={24} className="text-blue-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 text-lg">
                    {item.fileName || 'Documento sin nombre'}
                  </h4>
                  <div className="flex items-center space-x-3 mt-1">
                    <span className={getStatusBadge(item.status)}>
                      {getStatusIcon(item.status)}
                      <span className="ml-1">{item.status}</span>
                    </span>
                    {item.runId && (
                      <span className="text-xs text-gray-500">
                        ID: {item.runId.slice(0, 8)}...
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              {item.runId && (
                <div className="flex space-x-2">
                  {/* Botón para ver análisis de IA */}
                  {item.status === 'COMPLETED' && (
                    <button
                      onClick={() => toggleAnalysis(item.runId)}
                      className={`px-4 py-2.5 rounded-lg transition-all flex items-center space-x-2 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 ${
                        expandedItems.has(item.runId) 
                          ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white'
                          : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600'
                      }`}
                      title={expandedItems.has(item.runId) ? "Ocultar análisis IA" : "Ver análisis IA"}
                      disabled={loadingAnalysis.has(item.runId)}
                    >
                      {loadingAnalysis.has(item.runId) ? (
                        <IconLoader size={20} className="animate-spin" />
                      ) : (
                        <IconBrain size={20} />
                      )}
                      <span className="font-medium">
                        {loadingAnalysis.has(item.runId) 
                          ? 'Cargando...' 
                          : expandedItems.has(item.runId) 
                            ? 'Ocultar Análisis' 
                            : 'Ver Análisis IA'}
                      </span>
                    </button>
                  )}
                </div>
              )}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center text-gray-600 mb-1">
                  <IconCalendar size={16} className="mr-2" />
                  <span className="text-xs font-medium">Fecha de Procesamiento</span>
                </div>
                <p className="text-sm text-gray-900 font-medium">
                  {formatLocalDateTime(item.processedAt)}
                </p>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center text-gray-600 mb-1">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <span className="text-xs font-medium">Modelo de Análisis</span>
                </div>
                <p className="text-sm text-gray-900 font-medium">
                  {getModelName(item.model)}
                </p>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center text-gray-600 mb-1">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span className="text-xs font-medium">Estado del Texto</span>
                </div>
                <p className="text-sm text-gray-900 font-medium">
                  {item.textExtracted === 'EXTRACTED' ? 'Extraído con éxito' : item.textExtracted}
                </p>
              </div>
            </div>

            {item.completedAt && (
              <div className="text-xs text-gray-500 mb-2">
                <span className="font-medium">Completado:</span> {formatLocalDateTime(item.completedAt, 'long')}
              </div>
            )}

            {/* Expanded Analysis Section */}
            {expandedItems.has(item.runId) && item.runId && (
              <div className="mt-4 border-t-2 border-purple-200 pt-4 animate-fadeIn">
                <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-5 shadow-lg">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center space-x-2">
                      <IconBrain size={24} className="text-purple-600" />
                      <h5 className="text-xl font-bold text-purple-900">
                        Análisis de Inteligencia Artificial
                      </h5>
                    </div>
                    {(item.analysis || item.analysisResult || item.bedrockResult) && (
                      <button
                        onClick={() => {
                          const textToCopy = item.analysis || item.analysisResult || item.bedrockResult || '';
                          navigator.clipboard.writeText(textToCopy);
                          // Visual feedback
                          const btn = event?.currentTarget as HTMLButtonElement;
                          if (btn) {
                            btn.classList.add('bg-green-100');
                            setTimeout(() => btn.classList.remove('bg-green-100'), 1000);
                          }
                        }}
                        className="p-2 rounded-lg hover:bg-purple-100 transition-all duration-200"
                        title="Copiar análisis al portapapeles"
                      >
                        <IconCopy size={20} className="text-purple-600" />
                      </button>
                    )}
                  </div>
                  
                  {loadingAnalysis.has(item.runId) ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="flex flex-col items-center">
                        <IconLoader size={32} className="animate-spin text-purple-600 mb-3" />
                        <span className="text-purple-700 font-medium">Cargando análisis de IA...</span>
                      </div>
                    </div>
                  ) : (item.analysis || item.analysisResult || item.bedrockResult) ? (
                    <div className="bg-white rounded-lg p-6 shadow-inner border border-purple-100">
                      <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap leading-relaxed">
                        {item.analysis || item.analysisResult || item.bedrockResult}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                      <p className="text-yellow-800 flex items-center">
                        <IconAlertCircle size={20} className="mr-2" />
                        No hay análisis de IA disponible para este documento
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {item.errorMessage && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start mt-4">
                <IconAlertCircle size={18} className="text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-900">Error en el procesamiento:</p>
                  <p className="text-sm text-red-700 mt-1">{item.errorMessage}</p>
                </div>
              </div>
            )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}