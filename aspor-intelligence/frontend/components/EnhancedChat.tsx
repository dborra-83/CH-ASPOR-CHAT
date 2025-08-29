import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  IconCopy, 
  IconCheck, 
  IconUser, 
  IconRobot,
  IconLoader2,
  IconInfoCircle,
  IconCircleCheck,
  IconAlertCircle,
  IconClock,
  IconFileText,
  IconDatabase,
  IconBrain,
  IconFileAnalytics
} from '@tabler/icons-react';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

interface EnhancedChatProps {
  messages: Message[];
  loading?: boolean;
  currentProcess?: string;
}

export default function EnhancedChat({ messages, loading, currentProcess }: EnhancedChatProps) {
  const [copiedId, setCopiedId] = React.useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const getSystemIcon = (content: string) => {
    if (content.includes('Obteniendo URL')) return <IconDatabase size={16} />;
    if (content.includes('Subiendo archivo')) return <IconFileText size={16} />;
    if (content.includes('Extrayendo texto')) return <IconFileAnalytics size={16} />;
    if (content.includes('Analizando')) return <IconBrain size={16} />;
    if (content.includes('✅')) return <IconCircleCheck size={16} />;
    if (content.includes('⏳')) return <IconClock size={16} />;
    if (content.includes('Error')) return <IconAlertCircle size={16} />;
    return <IconInfoCircle size={16} />;
  };

  const getSystemColor = (content: string) => {
    if (content.includes('✅')) return 'from-green-50 to-emerald-50 border-green-200 text-green-900';
    if (content.includes('⏳')) return 'from-blue-50 to-indigo-50 border-blue-200 text-blue-900';
    if (content.includes('Error')) return 'from-red-50 to-pink-50 border-red-200 text-red-900';
    return 'from-purple-50 to-indigo-50 border-purple-200 text-purple-900';
  };

  const formatAnalysisContent = (content: string) => {
    // Add proper formatting for analysis results
    const formatted = content
      .replace(/^#+\s/gm, '\n### ')  // Ensure headers have proper spacing
      .replace(/\n\n+/g, '\n\n')      // Normalize line breaks
      .replace(/^-\s/gm, '• ')        // Replace dashes with bullets
      .replace(/^\d+\.\s/gm, (match) => `\n${match}`); // Add spacing before numbered lists
    
    return formatted;
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-gray-50 to-white">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={message.id}
            className={`flex ${
              message.type === 'user' ? 'justify-end' : 'justify-start'
            } animate-fadeIn`}
            style={{ animationDelay: `${index * 50}ms` }}
          >
            {message.type === 'user' ? (
              <div className="max-w-3xl flex items-start space-x-3">
                <div className="flex-1">
                  <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 rounded-2xl rounded-tr-sm shadow-lg">
                    <div className="flex items-center mb-2">
                      <IconUser size={18} className="mr-2" />
                      <span className="text-sm font-medium opacity-90">Usuario</span>
                    </div>
                    <p className="text-sm leading-relaxed">{message.content}</p>
                  </div>
                  <div className="text-xs text-gray-500 mt-1 text-right">
                    {new Date(message.timestamp).toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                </div>
              </div>
            ) : message.type === 'system' ? (
              <div className="max-w-3xl w-full">
                <div className={`bg-gradient-to-r ${getSystemColor(message.content)} p-3 rounded-xl border shadow-sm`}>
                  <div className="flex items-center space-x-2">
                    {getSystemIcon(message.content)}
                    <span className="text-sm font-medium">{message.content}</span>
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {new Date(message.timestamp).toLocaleTimeString('es-ES', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
              </div>
            ) : (
              <div className="max-w-4xl w-full">
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                  {/* Header */}
                  <div className="bg-gradient-to-r from-purple-600 to-pink-600 px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-white">
                      <IconRobot size={20} />
                      <span className="font-semibold">Análisis IA - Claude 3.5 Sonnet</span>
                    </div>
                    <button
                      onClick={() => copyToClipboard(message.content, message.id)}
                      className="p-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors text-white"
                      title="Copiar análisis"
                    >
                      {copiedId === message.id ? (
                        <IconCheck size={18} />
                      ) : (
                        <IconCopy size={18} />
                      )}
                    </button>
                  </div>
                  
                  {/* Content */}
                  <div className="p-6">
                    <div className="prose prose-sm max-w-none 
                      prose-headings:text-purple-900 prose-headings:font-bold 
                      prose-h3:text-lg prose-h3:mt-4 prose-h3:mb-3
                      prose-p:text-gray-700 prose-p:leading-relaxed prose-p:mb-3
                      prose-ul:my-3 prose-ul:space-y-2
                      prose-li:text-gray-700 prose-li:leading-relaxed
                      prose-strong:text-purple-700 prose-strong:font-semibold
                      prose-em:text-gray-600
                      prose-blockquote:border-l-4 prose-blockquote:border-purple-500 
                      prose-blockquote:pl-4 prose-blockquote:italic prose-blockquote:text-gray-600"
                    >
                      <ReactMarkdown>
                        {formatAnalysisContent(message.content)}
                      </ReactMarkdown>
                    </div>
                  </div>
                  
                  {/* Footer */}
                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 px-4 py-2 border-t border-purple-100">
                    <div className="text-xs text-purple-600 flex items-center justify-between">
                      <span>Análisis completado</span>
                      <span>
                        {new Date(message.timestamp).toLocaleTimeString('es-ES', {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit'
                        })}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="max-w-3xl w-full">
              <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 p-4 rounded-xl shadow-sm">
                <div className="flex items-center space-x-3">
                  <IconLoader2 size={24} className="animate-spin text-purple-600" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-purple-900">
                      {currentProcess || 'Procesando...'}
                    </p>
                    <div className="flex space-x-1 mt-2">
                      <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" />
                      <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse delay-100" />
                      <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse delay-200" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}