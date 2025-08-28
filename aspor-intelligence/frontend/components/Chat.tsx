import React from 'react';
import ReactMarkdown from 'react-markdown';
import { IconCopy, IconCheck } from '@tabler/icons-react';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

interface ChatProps {
  messages: Message[];
  loading?: boolean;
}

export default function Chat({ messages, loading }: ChatProps) {
  const [copiedId, setCopiedId] = React.useState<string | null>(null);

  const copyToClipboard = async (text: string, id: string) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback for older browsers or non-secure contexts
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        textArea.remove();
      }
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      // Try fallback method
      try {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        textArea.remove();
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
      } catch (fallbackErr) {
        console.error('Fallback copy also failed:', fallbackErr);
      }
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.type === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`w-full sm:max-w-3xl p-3 sm:p-4 rounded-lg shadow-sm ${
                message.type === 'user'
                  ? 'bg-blue-50 text-blue-900 ml-4 sm:ml-8'
                  : message.type === 'system'
                  ? 'bg-yellow-50 text-yellow-900 mr-4 sm:mr-8'
                  : 'bg-gray-50 text-gray-900 mr-4 sm:mr-8'
              }`}
            >
              {message.type === 'assistant' && (
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-medium text-gray-500">
                    Análisis AI
                  </span>
                  <button
                    onClick={() => copyToClipboard(message.content, message.id)}
                    className="ml-2 p-1 rounded hover:bg-gray-200 transition-colors"
                    title="Copiar al portapapeles"
                  >
                    {copiedId === message.id ? (
                      <IconCheck size={16} className="text-green-600" />
                    ) : (
                      <IconCopy size={16} className="text-gray-600" />
                    )}
                  </button>
                </div>
              )}
              
              <div className="prose prose-sm sm:prose-base max-w-none prose-p:my-2 prose-li:my-1 prose-headings:mt-3 prose-headings:mb-2">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
              
              <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-500">
                {new Date(message.timestamp).toLocaleTimeString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                  hour12: false
                })}
              </div>
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}