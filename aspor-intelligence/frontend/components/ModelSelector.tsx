import React from 'react';
import { IconBriefcase, IconUsers } from '@tabler/icons-react';

interface ModelSelectorProps {
  selectedModel: 'A' | 'B';
  onModelChange: (model: 'A' | 'B') => void;
  disabled?: boolean;
}

export default function ModelSelector({ 
  selectedModel, 
  onModelChange,
  disabled = false 
}: ModelSelectorProps) {
  const models = [
    {
      id: 'A',
      name: 'Contragarantías',
      description: 'Análisis de documentos legales',
      fullDescription: 'Identifica y analiza contragarantías, compromisos de respaldo y cláusulas en contratos legales',
      icon: IconBriefcase,
      color: 'blue'
    },
    {
      id: 'B',
      name: 'Informes Sociales',
      description: 'Evaluación socioeconómica',
      fullDescription: 'Procesa informes sociales para obtener insights estructurados de situaciones complejas',
      icon: IconUsers,
      color: 'green'
    }
  ];

  return (
    <div className="w-full space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        Modelo de Análisis
      </label>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {models.map((model) => {
          const Icon = model.icon;
          const isSelected = selectedModel === model.id;
          
          return (
            <button
              key={model.id}
              onClick={() => onModelChange(model.id as 'A' | 'B')}
              disabled={disabled}
              className={`
                relative p-4 rounded-xl border-2 transition-all duration-200 text-left
                ${isSelected 
                  ? model.color === 'blue'
                    ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-blue-100/50 shadow-md'
                    : 'border-green-500 bg-gradient-to-br from-green-50 to-green-100/50 shadow-md'
                  : 'border-gray-200 hover:border-gray-300 bg-white hover:shadow-sm'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              {/* Selection indicator */}
              {isSelected && (
                <div className="absolute top-3 right-3">
                  <div className={`
                    w-6 h-6 rounded-full flex items-center justify-center
                    ${model.color === 'blue' ? 'bg-blue-500' : 'bg-green-500'}
                  `}>
                    <svg className="w-4 h-4 text-white" fill="none" strokeWidth="3" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                </div>
              )}

              <div className="flex flex-col space-y-2">
                {/* Header with icon and title */}
                <div className="flex items-center space-x-3">
                  <div className={`
                    p-2.5 rounded-lg
                    ${isSelected 
                      ? model.color === 'blue'
                        ? 'bg-blue-200/50 text-blue-700'
                        : 'bg-green-200/50 text-green-700'
                      : 'bg-gray-100 text-gray-600'
                    }
                  `}>
                    <Icon size={22} />
                  </div>
                  <div className="flex-1">
                    <h3 className={`
                      font-semibold text-base
                      ${isSelected 
                        ? model.color === 'blue'
                          ? 'text-blue-900'
                          : 'text-green-900'
                        : 'text-gray-900'
                      }
                    `}>
                      {model.name}
                    </h3>
                    <p className={`
                      text-xs
                      ${isSelected 
                        ? model.color === 'blue'
                          ? 'text-blue-600'
                          : 'text-green-600'
                        : 'text-gray-500'
                      }
                    `}>
                      {model.description}
                    </p>
                  </div>
                </div>

                {/* Description - Only show on larger screens or when selected */}
                <p className={`
                  text-xs leading-relaxed
                  ${isSelected ? 'block' : 'hidden lg:block'}
                  ${isSelected 
                    ? model.color === 'blue'
                      ? 'text-blue-700'
                      : 'text-green-700'
                    : 'text-gray-600'
                  }
                `}>
                  {model.fullDescription}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}