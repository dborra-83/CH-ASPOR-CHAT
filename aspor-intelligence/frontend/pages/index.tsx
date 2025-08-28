import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { IconBrain, IconHistory as IconHistoryTab, IconSettings, IconFileAnalytics } from '@tabler/icons-react';

import Chat from '../components/Chat';
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

      const { runId, textKey } = extractRes.data;

      // Step 4: Analyze with Bedrock
      addMessage('system', `Analizando con modelo ${selectedModel === 'A' ? 'Contragarantías' : 'Informes Sociales'}...`);
      const analyzeRes = await axios.post(`${baseUrl}/analyze`, {
        userId,
        runId,
        model: selectedModel,
        textKey
      });

      // Step 5: Show result
      addMessage('assistant', analyzeRes.data.analysis);
      
      // Clear file after successful processing
      setSelectedFile(null);

    } catch (error: any) {
      console.error('Error processing document:', error);
      addMessage('system', `Error: ${error.response?.data?.error || error.message || 'Error desconocido'}`);
    } finally {
      setProcessing(false);
    }
  };

  const viewHistoryResult = async (runId: string) => {
    try {
      const baseUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
      const response = await axios.get(`${baseUrl}/runs/${runId}`);
      setActiveTab('chat');
      setMessages([]);
      addMessage('system', `Mostrando resultado del procesamiento ${runId}`);
      if (response.data.analysis) {
        addMessage('assistant', response.data.analysis);
      }
    } catch (error) {
      console.error('Error loading result:', error);
      addMessage('system', 'Error al cargar el resultado del historial');
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
                          📄 Límite: 15,000 caracteres
                        </p>
                        <p className="text-xs text-blue-600 mt-1">
                          📊 Formatos: PDF, PNG, JPG
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
                      <Chat messages={messages} loading={processing} />
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