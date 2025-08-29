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
  IconClipboardList,
  IconHash,
  IconTable,
  IconListDetails,
  IconPoint,
  IconCheckbox
} from '@tabler/icons-react';

interface AnalysisFormatterProps {
  content: string;
  modelType?: string;
}

export default function AnalysisFormatter({ content, modelType }: AnalysisFormatterProps) {
  if (!content) return null;

  // Function to format tables if detected
  const formatTable = (text: string): JSX.Element | null => {
    // Detect if text contains table-like structure (multiple | in lines)
    const lines = text.split('\n');
    const tableLines = lines.filter(line => (line.match(/\|/g) || []).length >= 2);
    
    if (tableLines.length < 2) return null;

    const rows = tableLines.map(line => 
      line.split('|').map(cell => cell.trim()).filter(cell => cell)
    );

    if (rows.length < 2) return null;

    return (
      <div className="overflow-x-auto mb-6">
        <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg overflow-hidden">
          <thead className="bg-gradient-to-r from-purple-50 to-indigo-50">
            <tr>
              {rows[0].map((header, idx) => (
                <th key={idx} className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {rows.slice(1).map((row, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-gray-50 transition-colors">
                {row.map((cell, cellIdx) => (
                  <td key={cellIdx} className="px-4 py-3 text-sm text-gray-700">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // Enhanced function to detect and format sections
  const formatAnalysis = (text: string) => {
    const lines = text.split('\n');
    const formatted: JSX.Element[] = [];
    let currentSection: string[] = [];
    let listItems: string[] = [];
    let tableBuffer: string[] = [];
    let codeBlock: string[] = [];
    let inCodeBlock = false;

    const getIconForSection = (title: string) => {
      const lowerTitle = title.toLowerCase();
      if (lowerTitle.includes('contragarantía') || lowerTitle.includes('garantía')) {
        return <IconShieldCheck className="text-purple-600" size={22} />;
      }
      if (lowerTitle.includes('parte') || lowerTitle.includes('involucrada')) {
        return <IconUsers className="text-blue-600" size={22} />;
      }
      if (lowerTitle.includes('condicion') || lowerTitle.includes('término')) {
        return <IconClipboardList className="text-green-600" size={22} />;
      }
      if (lowerTitle.includes('plazo') || lowerTitle.includes('vigencia') || lowerTitle.includes('fecha')) {
        return <IconCalendar className="text-orange-600" size={22} />;
      }
      if (lowerTitle.includes('riesgo')) {
        return <IconAlertTriangle className="text-red-600" size={22} />;
      }
      if (lowerTitle.includes('situación') || lowerTitle.includes('económic')) {
        return <IconCurrencyDollar className="text-green-600" size={22} />;
      }
      if (lowerTitle.includes('recomendac')) {
        return <IconBulb className="text-yellow-600" size={22} />;
      }
      if (lowerTitle.includes('plan') || lowerTitle.includes('acción')) {
        return <IconTarget className="text-indigo-600" size={22} />;
      }
      if (lowerTitle.includes('resumen') || lowerTitle.includes('conclusi')) {
        return <IconListDetails className="text-teal-600" size={22} />;
      }
      if (lowerTitle.includes('dato') || lowerTitle.includes('información')) {
        return <IconTable className="text-cyan-600" size={22} />;
      }
      return <IconFileText className="text-gray-600" size={22} />;
    };

    const renderListItems = (items: string[], index: number) => {
      if (items.length === 0) return null;
      
      return (
        <div key={`list-${index}`} className="ml-2 mb-4">
          <div className="bg-gradient-to-r from-gray-50 to-white rounded-lg p-4 border-l-4 border-purple-400">
            <ul className="space-y-3">
              {items.map((item, idx) => {
                // Check if item has sub-structure (contains : or -)
                const hasSubStructure = item.includes(':');
                
                if (hasSubStructure) {
                  const [label, value] = item.split(':').map(s => s.trim());
                  return (
                    <li key={idx} className="flex items-start group hover:bg-purple-50 rounded-lg p-2 transition-colors">
                      <IconPoint size={20} className="text-purple-500 mt-0.5 mr-3 flex-shrink-0" />
                      <div className="flex-1">
                        <span className="font-medium text-gray-800">{label}:</span>
                        {value && <span className="text-gray-700 ml-2">{value}</span>}
                      </div>
                    </li>
                  );
                }
                
                return (
                  <li key={idx} className="flex items-start group hover:bg-purple-50 rounded-lg p-2 transition-colors">
                    <IconChevronRight size={18} className="text-purple-500 mt-0.5 mr-3 flex-shrink-0" />
                    <span className="text-gray-700 leading-relaxed">{item}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      );
    };

    lines.forEach((line, index) => {
      const trimmedLine = line.trim();

      // Check for code blocks
      if (trimmedLine.startsWith('```')) {
        if (inCodeBlock) {
          // End code block
          formatted.push(
            <div key={`code-${index}`} className="mb-4">
              <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto">
                <code className="text-sm font-mono">{codeBlock.join('\n')}</code>
              </pre>
            </div>
          );
          codeBlock = [];
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
        }
        return;
      }

      if (inCodeBlock) {
        codeBlock.push(line);
        return;
      }

      // Check for table rows
      if ((line.match(/\|/g) || []).length >= 2) {
        tableBuffer.push(line);
        return;
      } else if (tableBuffer.length > 0) {
        // Process accumulated table
        const table = formatTable(tableBuffer.join('\n'));
        if (table) {
          formatted.push(<div key={`table-${index}`}>{table}</div>);
        }
        tableBuffer = [];
      }

      // Check for main headers with ### or ##
      if (/^#{1,3}\s/.test(trimmedLine)) {
        // Render any pending list items first
        const list = renderListItems(listItems, index);
        if (list) formatted.push(list);
        listItems = [];

        const headerText = trimmedLine.replace(/^#{1,3}\s/, '');
        const headerLevel = (trimmedLine.match(/^(#{1,3})/)?.[1].length || 1);
        
        formatted.push(
          <div key={`header-${index}`} className={`mb-4 ${headerLevel === 1 ? 'mt-6' : 'mt-4'}`}>
            <div className="flex items-center">
              {getIconForSection(headerText)}
              <h3 className={`ml-3 font-bold text-gray-800 ${
                headerLevel === 1 ? 'text-2xl' : headerLevel === 2 ? 'text-xl' : 'text-lg'
              }`}>
                {headerText}
              </h3>
            </div>
            <div className="mt-2 h-1 bg-gradient-to-r from-purple-400 to-indigo-400 rounded-full w-24"></div>
          </div>
        );
      }
      // Check for numbered sections (1., 2., etc.) or sections with colons
      else if (/^\d+\./.test(trimmedLine) || /^[A-Z][^:]{0,50}:/.test(trimmedLine)) {
        // Render any pending list items first
        const list = renderListItems(listItems, index);
        if (list) formatted.push(list);
        listItems = [];

        const colonIndex = line.indexOf(':');
        if (colonIndex > 0 && colonIndex < 60) {
          const title = line.substring(0, colonIndex).replace(/^\d+\./, '').trim();
          const content = line.substring(colonIndex + 1).trim();
          
          formatted.push(
            <div key={`section-${index}`} className="mb-6 group">
              <div className="flex items-start">
                <div className="p-2 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-lg mr-3 group-hover:scale-110 transition-transform">
                  {getIconForSection(title)}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-800 mb-2">
                    {title}
                  </h3>
                  {content && (
                    <div className="p-4 bg-gradient-to-r from-gray-50 via-white to-gray-50 rounded-lg border-l-4 border-purple-400 shadow-sm">
                      <p className="text-gray-700 leading-relaxed">{content}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        } else {
          // Section without colon
          formatted.push(
            <div key={`section-${index}`} className="mb-4">
              <div className="flex items-center mb-2">
                {getIconForSection(trimmedLine)}
                <h3 className="ml-3 text-lg font-semibold text-gray-800">
                  {trimmedLine.replace(/^\d+\./, '').trim()}
                </h3>
              </div>
            </div>
          );
        }
      }
      // Check for list items
      else if (/^[-*•·✓✔➤→]/.test(trimmedLine) || /^\s+[-*•·]/.test(line)) {
        listItems.push(trimmedLine.replace(/^[-*•·✓✔➤→]\s*/, '').trim());
      }
      // Check for indented content or quotes
      else if (line.startsWith('  ') || line.startsWith('\t') || line.startsWith('>')) {
        const list = renderListItems(listItems, index);
        if (list) formatted.push(list);
        listItems = [];

        formatted.push(
          <div key={`quote-${index}`} className="mb-4 ml-4">
            <div className="border-l-4 border-indigo-400 pl-4 py-2 bg-indigo-50 rounded-r-lg">
              <p className="text-gray-700 italic leading-relaxed">
                {line.replace(/^[>\s]+/, '').trim()}
              </p>
            </div>
          </div>
        );
      }
      // Regular paragraphs
      else if (trimmedLine) {
        // Render any pending list items first
        const list = renderListItems(listItems, index);
        if (list) formatted.push(list);
        listItems = [];

        // Check for important keywords to highlight
        let formattedText = trimmedLine;
        const importantWords = ['IMPORTANTE', 'NOTA', 'ADVERTENCIA', 'ATENCIÓN', 'URGENTE'];
        
        if (importantWords.some(word => trimmedLine.includes(word))) {
          formatted.push(
            <div key={`alert-${index}`} className="mb-4">
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg">
                <div className="flex items-start">
                  <IconAlertTriangle className="text-yellow-600 mr-2 flex-shrink-0" size={20} />
                  <p className="text-gray-800 font-medium leading-relaxed">{formattedText}</p>
                </div>
              </div>
            </div>
          );
        } else {
          formatted.push(
            <p key={`para-${index}`} className="mb-4 text-gray-700 leading-relaxed text-base">
              {formattedText}
            </p>
          );
        }
      }
    });

    // Render any remaining items
    const finalList = renderListItems(listItems, lines.length);
    if (finalList) formatted.push(finalList);

    // Process any remaining table
    if (tableBuffer.length > 0) {
      const table = formatTable(tableBuffer.join('\n'));
      if (table) {
        formatted.push(<div key="table-final">{table}</div>);
      }
    }

    return formatted;
  };

  // Detect if content has some structure or needs basic formatting
  const hasStructure = content.includes(':') || /\d+\./.test(content) || content.includes('#');

  return (
    <div className="analysis-formatted">
      {/* Enhanced header */}
      <div className="mb-8 pb-4 border-b-2 border-gradient-to-r from-purple-300 to-indigo-300">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="p-3 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-xl mr-4 shadow-md">
              <IconFileText size={28} className="text-purple-600" />
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Tipo de Análisis</h4>
              <p className="text-xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
                {modelType === 'A' ? 'Análisis de Contragarantías' : 
                 modelType === 'B' ? 'Análisis de Informe Social' : 
                 'Análisis de Documento'}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className="px-4 py-2 bg-gradient-to-r from-green-100 to-emerald-100 text-green-700 rounded-full text-sm font-medium flex items-center shadow-sm">
              <IconCircleCheck size={18} className="mr-2" />
              Análisis Completado
            </span>
          </div>
        </div>
      </div>

      {/* Main content with enhanced styling */}
      <div className="space-y-6 max-w-none">
        {hasStructure ? (
          <div className="animate-fadeIn">
            {formatAnalysis(content)}
          </div>
        ) : (
          // If no structure detected, show as clean formatted paragraphs
          <div className="p-6 bg-gradient-to-br from-gray-50 to-white rounded-xl shadow-sm border border-gray-200">
            <div className="prose prose-gray max-w-none">
              {content.split('\n\n').map((paragraph, idx) => (
                <p key={idx} className="mb-4 text-gray-700 leading-relaxed text-base last:mb-0">
                  {paragraph}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Enhanced footer */}
      <div className="mt-8 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center text-gray-500">
            <IconInfoCircle size={18} className="mr-2" />
            <span>Análisis generado por Claude 3.5 Sonnet vía Amazon Bedrock</span>
          </div>
          <div className="flex items-center space-x-4">
            <button className="text-purple-600 hover:text-purple-700 font-medium flex items-center group">
              <IconCheckbox size={18} className="mr-1 group-hover:scale-110 transition-transform" />
              Verificado
            </button>
          </div>
        </div>
      </div>

      {/* Add some CSS animations */}
      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.5s ease-out;
        }
      `}</style>
    </div>
  );
}