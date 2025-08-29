import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { IconBrain, IconHistory as IconHistoryTab, IconSettings, IconFileAnalytics } from '@tabler/icons-react';

import EnhancedChat from '../components/EnhancedChat';
import FileUploader from '../components/FileUploader';
import ModelSelector from '../components/ModelSelector';
import HistoryViewer from '../components/HistoryViewer';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export default function Home() {
  const [apiUrl, setApiUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedModel, setSelectedModel] = useState<'A' | 'B'>('A');
  const [messages, setMessages] = useState<Message[]>([]);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState<'chat' | 'history'>('chat');
  const [currentProcess, setCurrentProcess] = useState<string>('');
  const userId = 'web-user';

  useEffect(() => {
    // Load API URL from config
    fetch('/config.json')
      .then(res => res.json())
      .then(config => setApiUrl(config.apiUrl))
      .catch(() => {
        // Fallback for development
        setApiUrl(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001');
      });
  }, []);

  const addMessage = (type: Message['type'], content: string) => {
    const newMessage: Message = {
      id: uuidv4(),
      type,
      content,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMessage]);
    
    // Update current process for system messages
    if (type === 'system') {
      setCurrentProcess(content);
    }
  };

  const pollForAnalysisResult = async (baseUrl: string, runId: string) => {
    addMessage('system', '⏳ Procesando análisis con IA. Esto puede tomar 10-30 segundos...');
    
    let attempts = 0;
    const maxAttempts = 20; // 20 attempts * 3 seconds = 60 seconds max
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 3000)); // Wait 3 seconds
      
      try {
        const statusRes = await axios.get(`${baseUrl}/status/${runId}`);
        
        if (statusRes.data.status === 'COMPLETED') {
          if (statusRes.data.analysis) {
            addMessage('system', '✅ Análisis completado');
            addMessage('assistant', statusRes.data.analysis);
            return;
          } else {
            throw new Error('Análisis completado pero sin resultado');
          }
        } else if (statusRes.data.status === 'FAILED') {
          throw new Error(statusRes.data.error || 'Error en el análisis');
        }
        
        attempts++;
        if (attempts % 3 === 0) {
          addMessage('system', `⏳ Analizando documento... (${attempts * 3} segundos)`);
        }
      } catch (pollError: any) {
        console.error('Polling error:', pollError);
        if (attempts === maxAttempts - 1) {
          throw new Error('Timeout esperando el análisis del documento');
        }
      }
    }
    
    throw new Error('No se pudo completar el análisis en el tiempo esperado');
  };

  const processDocument = async () => {
    if (!selectedFile || !apiUrl) return;

    setProcessing(true);
    addMessage('user', `Procesando documento: ${selectedFile.name} con modelo ${selectedModel === 'A' ? 'Contragarantías' : 'Informes Sociales'}`);

    try {
      // Step 1: Get presigned URL
      addMessage('system', 'Obteniendo URL de carga...');
      const baseUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
      const presignedRes = await axios.post(`${baseUrl}/upload`, {
        fileName: selectedFile.name,
        fileType: selectedFile.type
      });

      const { uploadUrl, fileKey } = presignedRes.data;

      // Step 2: Upload file to S3
      addMessage('system', 'Subiendo archivo...');
      await axios.put(uploadUrl, selectedFile, {
        headers: {
          'Content-Type': selectedFile.type
        }
      });

      // Step 3: Extract text with Textract
      addMessage('system', 'Extrayendo texto con AWS Textract...');
      const extractRes = await axios.post(`${baseUrl}/extract`, {
        userId,
        fileKey
      });

      // Check if async processing is required
      if (extractRes.status === 202 || extractRes.data.status === 'PROCESSING_ASYNC') {
        addMessage('system', '⏳ El documento contiene imágenes escaneadas y está siendo procesado. Esto puede tomar hasta 30 segundos...');
        
        // Poll for status
        let attempts = 0;
        const maxAttempts = 10;
        let runId = extractRes.data.runId;
        let textKey = null;
        
        while (attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 3000)); // Wait 3 seconds
          
          try {
            const statusRes = await axios.get(`${baseUrl}/runs/${runId}`);
            
            if (statusRes.data.status === 'EXTRACTED') {
              textKey = statusRes.data.textKey;
              addMessage('system', '✅ Texto extraído exitosamente');
              break;
            } else if (statusRes.data.status === 'FAILED') {
              throw new Error(statusRes.data.errorMessage || 'Error en extracción');
            }
            
            attempts++;
            if (attempts % 2 === 0) {
              addMessage('system', `⏳ Procesando... (${attempts * 3} segundos)`);
            }
          } catch (pollError) {
            console.error('Polling error:', pollError);
            if (attempts === maxAttempts - 1) {
              throw new Error('Timeout esperando el procesamiento del documento');
            }
          }
        }
        
        if (!textKey) {
          throw new Error('No se pudo obtener el texto extraído después de esperar');
        }
        
        // Continue with the extracted text
        const finalRunId = runId;
        const finalTextKey = textKey;
        
        // Step 4: Analyze with Bedrock (for async case)
        addMessage('system', `Analizando con modelo ${selectedModel === 'A' ? 'Contragarantías' : 'Informes Sociales'}...`);
        const analyzeRes = await axios.post(`${baseUrl}/analyze`, {
          userId,
          runId: finalRunId,
          model: selectedModel,
          textKey: finalTextKey
        });
        
        // Check if analysis is async
        if (analyzeRes.status === 202) {
          await pollForAnalysisResult(baseUrl, finalRunId);
        } else if (analyzeRes.data.analysis) {
          addMessage('assistant', analyzeRes.data.analysis);
        }
      } else {
        // Normal synchronous processing
        const { runId, textKey } = extractRes.data;

        // Step 4: Analyze with Bedrock
        addMessage('system', `Analizando con modelo ${selectedModel === 'A' ? 'Contragarantías' : 'Informes Sociales'}...`);
        const analyzeRes = await axios.post(`${baseUrl}/analyze`, {
          userId,
          runId,
          model: selectedModel,
          textKey
        });
        
        // Check if analysis is async (202 status)
        if (analyzeRes.status === 202) {
          await pollForAnalysisResult(baseUrl, runId);
        } else if (analyzeRes.data.analysis) {
          // Step 5: Show result
          addMessage('assistant', analyzeRes.data.analysis);
        }
      }
      
      // Clear file after successful processing
      setSelectedFile(null);

    } catch (error: any) {
      console.error('Error processing document:', error);
      addMessage('system', `Error: ${error.response?.data?.error || error.message || 'Error desconocido'}`);
    } finally {
      setProcessing(false);
      setCurrentProcess('');
    }
  };

  const viewHistoryResult = async (runId: string) => {
    try {
      const baseUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
      
      // First try the new status endpoint
      let response;
      try {
        response = await axios.get(`${baseUrl}/status/${runId}`);
      } catch (err) {
        // Fallback to old endpoint if new one fails
        response = await axios.get(`${baseUrl}/runs/${runId}`);
      }
      
      setActiveTab('chat');
      setMessages([]);
      addMessage('system', `Mostrando resultado del procesamiento ${runId}`);
      
      // Check if analysis is available
      if (response.data.analysis) {
        addMessage('assistant', response.data.analysis);
      } else if (response.data.analysisResult) {
        // Check for analysisResult field (from DynamoDB)
        addMessage('assistant', response.data.analysisResult);
      } else if (response.data.bedrockResult) {
        // Check for bedrockResult field (legacy)
        addMessage('assistant', response.data.bedrockResult);
      } else if (response.data.status === 'PROCESSING_ASYNC' || response.data.status === 'PROCESSING') {
        addMessage('system', '⏳ El documento aún se está procesando. Por favor, intenta nuevamente en unos segundos.');
      } else {
        addMessage('system', 'No se encontró el análisis para este documento. Es posible que necesite ser reprocesado.');
      }
    } catch (error: any) {
      console.error('Error loading result:', error);
      addMessage('system', `Error al cargar el resultado: ${error.message || 'Error desconocido'}`);
    }
  };

  return (
    <>
      <Head>
        <title>ASPOR Intelligence - Análisis de Documentos</title>
        <meta name="description" content="Sistema de análisis inteligente de documentos legales y sociales" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
          <div className="px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-3">
                <IconBrain size={28} className="text-blue-600" />
                <h1 className="text-xl font-bold text-gray-900">
                  ASPOR Intelligence
                </h1>
              </div>
              
              <div className="hidden sm:flex items-center space-x-2">
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`px-4 py-2 rounded-lg font-medium transition-all ${
                    activeTab === 'chat'
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <IconFileAnalytics size={18} />
                    <span>Análisis</span>
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('history')}
                  className={`px-4 py-2 rounded-lg font-medium transition-all ${
                    activeTab === 'history'
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <IconHistoryTab size={18} />
                    <span>Historial</span>
                  </div>
                </button>
              </div>

              {/* Mobile tabs */}
              <div className="flex sm:hidden space-x-1">
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`p-2 rounded-lg ${
                    activeTab === 'chat' ? 'bg-blue-600 text-white' : 'text-gray-600'
                  }`}
                >
                  <IconFileAnalytics size={20} />
                </button>
                <button
                  onClick={() => setActiveTab('history')}
                  className={`p-2 rounded-lg ${
                    activeTab === 'history' ? 'bg-blue-600 text-white' : 'text-gray-600'
                  }`}
                >
                  <IconHistoryTab size={20} />
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto" style={{ height: 'calc(100vh - 4rem)' }}>
          {activeTab === 'chat' ? (
            <div className="container mx-auto max-w-7xl p-4 lg:p-6">
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                {/* Configuration Section */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
                    <IconSettings size={20} className="mr-2" />
                    Configuración
                  </h2>
                  
                  <div className="space-y-6">
                    {/* File Uploader */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Documento
                      </label>
                      <FileUploader
                        onFileSelect={setSelectedFile}
                        selectedFile={selectedFile}
                        onClear={() => setSelectedFile(null)}
                        disabled={processing}
                      />
                    </div>
                    
                    {/* Model Selector */}
                    <ModelSelector
                      selectedModel={selectedModel}
                      onModelChange={setSelectedModel}
                      disabled={processing}
                    />
                    
                    {/* Process Button */}
                    <button
                      onClick={processDocument}
                      disabled={!selectedFile || processing || !apiUrl}
                      className={`
                        w-full py-3 px-4 rounded-lg font-medium transition-all
                        flex items-center justify-center space-x-2
                        ${!selectedFile || processing || !apiUrl
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                          : 'bg-gradient-to-r from-blue-600 to-blue-700 text-white hover:from-blue-700 hover:to-blue-800 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5'
                        }
                      `}
                    >
                      {processing ? (
                        <>
                          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          <span>Procesando...</span>
                        </>
                      ) : (
                        <>
                          <IconFileAnalytics size={20} />
                          <span>Procesar Documento</span>
                        </>
                      )}
                    </button>

                    {/* Info Card */}
                    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-100">
                      <h3 className="text-sm font-semibold text-blue-900 mb-2">
                        Información del Sistema
                      </h3>
                      <p className="text-xs text-blue-700 leading-relaxed">
                        Utiliza AWS Textract para extraer texto y Claude 3 Sonnet para análisis inteligente.
                      </p>
                      <div className="mt-3 pt-3 border-t border-blue-200">
                        <p className="text-xs text-blue-600">
                          📄 Límite: 30,000 caracteres de entrada
                        </p>
                        <p className="text-xs text-blue-600 mt-1">
                          📝 Resultado: Hasta 10,000 caracteres
                        </p>
                        <p className="text-xs text-blue-600 mt-1">
                          📊 Formato: Solo PDF
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Results Section */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col" style={{ minHeight: '600px' }}>
                  <div className="border-b border-gray-200 px-6 py-4">
                    <h2 className="text-lg font-semibold text-gray-900">
                      Resultados del Análisis
                    </h2>
                    <p className="text-sm text-gray-500">
                      {messages.length > 0 
                        ? `${messages.length} mensajes en la conversación`
                        : 'Sube un documento para comenzar'}
                    </p>
                  </div>
                  
                  <div className="flex-1 bg-gray-50 rounded-b-xl overflow-hidden">
                    {messages.length === 0 ? (
                      <div className="flex items-center justify-center h-full min-h-[400px]">
                        <div className="text-center max-w-md mx-auto p-8">
                          <IconBrain size={64} className="mx-auto mb-4 text-gray-300" />
                          <h3 className="text-lg font-medium text-gray-900 mb-2">
                            Comienza tu análisis
                          </h3>
                          <p className="text-gray-500 text-sm">
                            Selecciona un documento y el modelo de análisis para obtener insights inteligentes impulsados por IA
                          </p>
                        </div>
                      </div>
                    ) : (
                      <EnhancedChat messages={messages} loading={processing} currentProcess={currentProcess} />
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="container mx-auto max-w-7xl p-4 lg:p-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <HistoryViewer
                  userId={userId}
                  apiUrl={apiUrl}
                  onViewResult={viewHistoryResult}
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </>
  );
}