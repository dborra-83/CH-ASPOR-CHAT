import React from 'react';
import { 
  IconCircleCheck, 
  IconAlertTriangle, 
  IconInfoCircle,
  IconChevronRight,
  IconFileText,
  IconUsers,
  IconCalendar,
  IconShieldCheck,
  IconCurrencyDollar,
  IconBulb,
  IconTarget,
  IconClipboardList
} from '@tabler/icons-react';

interface AnalysisFormatterProps {
  content: string;
  modelType?: string;
}

export default function AnalysisFormatter({ content, modelType }: AnalysisFormatterProps) {
  if (!content) return null;

  // Function to detect and format sections
  const formatAnalysis = (text: string) => {
    // Split by line breaks
    const lines = text.split('\n').filter(line => line.trim());
    const formatted: JSX.Element[] = [];
    let currentSection: string[] = [];
    let inList = false;
    let listItems: string[] = [];

    const getIconForSection = (title: string) => {
      const lowerTitle = title.toLowerCase();
      if (lowerTitle.includes('contragarantía') || lowerTitle.includes('garantía')) {
        return <IconShieldCheck className="text-purple-600" size={20} />;
      }
      if (lowerTitle.includes('parte') || lowerTitle.includes('involucrada')) {
        return <IconUsers className="text-blue-600" size={20} />;
      }
      if (lowerTitle.includes('condicion') || lowerTitle.includes('término')) {
        return <IconClipboardList className="text-green-600" size={20} />;
      }
      if (lowerTitle.includes('plazo') || lowerTitle.includes('vigencia') || lowerTitle.includes('fecha')) {
        return <IconCalendar className="text-orange-600" size={20} />;
      }
      if (lowerTitle.includes('riesgo')) {
        return <IconAlertTriangle className="text-red-600" size={20} />;
      }
      if (lowerTitle.includes('situación') || lowerTitle.includes('económic')) {
        return <IconCurrencyDollar className="text-green-600" size={20} />;
      }
      if (lowerTitle.includes('recomendac')) {
        return <IconBulb className="text-yellow-600" size={20} />;
      }
      if (lowerTitle.includes('plan') || lowerTitle.includes('acción')) {
        return <IconTarget className="text-indigo-600" size={20} />;
      }
      if (lowerTitle.includes('recurso')) {
        return <IconInfoCircle className="text-teal-600" size={20} />;
      }
      return <IconFileText className="text-gray-600" size={20} />;
    };

    lines.forEach((line, index) => {
      // Check if it's a main title (usually numbered like "1.", "2.", etc. or contains ":")
      if (/^\d+\./.test(line) || (line.includes(':') && line.split(':')[0].length < 50)) {
        // If we have accumulated list items, render them first
        if (listItems.length > 0) {
          formatted.push(
            <ul key={`list-${index}`} className="ml-4 mb-4 space-y-2">
              {listItems.map((item, idx) => (
                <li key={idx} className="flex items-start">
                  <IconChevronRight size={16} className="text-purple-400 mt-1 mr-2 flex-shrink-0" />
                  <span className="text-gray-700 leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          );
          listItems = [];
        }

        const [title, ...rest] = line.split(':');
        const content = rest.join(':').trim();
        
        formatted.push(
          <div key={`section-${index}`} className="mb-6">
            <div className="flex items-center mb-2">
              {getIconForSection(title)}
              <h3 className="ml-2 text-lg font-semibold text-gray-800">
                {title.replace(/^\d+\./, '').trim()}
              </h3>
            </div>
            {content && (
              <div className="ml-7 p-3 bg-gray-50 rounded-lg border-l-4 border-purple-400">
                <p className="text-gray-700 leading-relaxed">{content}</p>
              </div>
            )}
          </div>
        );
      }
      // Check if it's a list item (starts with -, *, •, or similar)
      else if (/^[-*•·]/.test(line.trim())) {
        listItems.push(line.replace(/^[-*•·]\s*/, '').trim());
      }
      // Check if it's a sub-point (starts with spaces or tabs and then -)
      else if (/^\s+[-*•·]/.test(line)) {
        listItems.push(line.trim().replace(/^[-*•·]\s*/, ''));
      }
      // Regular paragraph
      else {
        // If we have accumulated list items, render them first
        if (listItems.length > 0) {
          formatted.push(
            <ul key={`list-${index}`} className="ml-4 mb-4 space-y-2">
              {listItems.map((item, idx) => (
                <li key={idx} className="flex items-start">
                  <IconChevronRight size={16} className="text-purple-400 mt-1 mr-2 flex-shrink-0" />
                  <span className="text-gray-700 leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          );
          listItems = [];
        }

        formatted.push(
          <p key={`para-${index}`} className="mb-4 text-gray-700 leading-relaxed">
            {line}
          </p>
        );
      }
    });

    // Render any remaining list items
    if (listItems.length > 0) {
      formatted.push(
        <ul key={`list-final`} className="ml-4 mb-4 space-y-2">
          {listItems.map((item, idx) => (
            <li key={idx} className="flex items-start">
              <IconChevronRight size={16} className="text-purple-400 mt-1 mr-2 flex-shrink-0" />
              <span className="text-gray-700 leading-relaxed">{item}</span>
            </li>
          ))}
        </ul>
      );
    }

    return formatted;
  };

  // Detect if content has some structure or needs basic formatting
  const hasStructure = content.includes(':') || /\d+\./.test(content);

  return (
    <div className="analysis-formatted">
      {/* Header based on model type */}
      <div className="mb-6 pb-3 border-b-2 border-purple-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg mr-3">
              <IconFileText size={24} className="text-purple-600" />
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500">Tipo de Análisis</h4>
              <p className="text-lg font-semibold text-gray-800">
                {modelType === 'A' ? 'Análisis de Contragarantías' : 
                 modelType === 'B' ? 'Análisis de Informe Social' : 
                 'Análisis de Documento'}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium flex items-center">
              <IconCircleCheck size={16} className="mr-1" />
              Completado
            </span>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="space-y-4">
        {hasStructure ? (
          formatAnalysis(content)
        ) : (
          // If no structure detected, show as clean paragraphs
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="prose prose-gray max-w-none">
              {content.split('\n\n').map((paragraph, idx) => (
                <p key={idx} className="mb-4 text-gray-700 leading-relaxed last:mb-0">
                  {paragraph}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Summary footer */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex items-center text-sm text-gray-500">
          <IconInfoCircle size={16} className="mr-2" />
          <span>Análisis generado por Claude 3 Sonnet vía Amazon Bedrock</span>
        </div>
      </div>
    </div>
  );
}