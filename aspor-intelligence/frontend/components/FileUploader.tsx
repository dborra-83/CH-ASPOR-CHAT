import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { IconUpload, IconFile, IconX } from '@tabler/icons-react';

interface FileUploaderProps {
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
  onClear: () => void;
  disabled?: boolean;
}

export default function FileUploader({ 
  onFileSelect, 
  selectedFile, 
  onClear,
  disabled = false 
}: FileUploaderProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxFiles: 1,
    disabled
  });

  return (
    <div className="w-full">
      {!selectedFile ? (
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
            transition-colors duration-200
            ${isDragActive 
              ? 'border-tabler-blue bg-blue-50' 
              : 'border-gray-300 hover:border-tabler-blue hover:bg-gray-50'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <input {...getInputProps()} />
          <IconUpload 
            size={48} 
            className="mx-auto mb-4 text-gray-400"
          />
          <p className="text-lg font-medium text-gray-700 mb-2">
            {isDragActive 
              ? 'Suelta el archivo PDF aquí' 
              : 'Arrastra un PDF o haz clic para seleccionar'
            }
          </p>
          <p className="text-sm text-gray-500">
            Formato soportado: Solo PDF
          </p>
          <p className="text-xs text-gray-400 mt-2">
            Tamaño máximo: 10MB
          </p>
        </div>
      ) : (
        <div className="tabler-card p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <IconFile size={32} className="text-tabler-blue" />
              <div>
                <p className="font-medium text-gray-900">
                  {selectedFile.name}
                </p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              onClick={onClear}
              disabled={disabled}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              title="Eliminar archivo"
            >
              <IconX size={20} className="text-gray-600" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}