import React from 'react';
import { Button } from './ui/button';
import { FileIcon, FolderIcon } from 'lucide-react';
import { pickFile, pickFolder } from '@/lib/tauri';

interface FilePickerProps {
  label: string;
  value: string;
  onChange: (path: string) => void;
  type?: 'file' | 'folder';
  filters?: Array<{ name: string; extensions: string[] }>;
  placeholder?: string;
  icon?: React.ReactNode;
  accept?: string;
  required?: boolean;
}

export function FilePicker({
  label,
  value,
  onChange,
  type = 'file',
  filters,
  placeholder = 'Click to select...',
  icon,
  required
}: FilePickerProps) {
  const handlePick = async () => {
    try {
      const path = type === 'folder' 
        ? await pickFolder()
        : await pickFile(filters);
      
      if (path) {
        onChange(path as string);
      }
    } catch (error) {
      console.error('Error picking file:', error);
    }
  };

  return (
    <div className="space-y-1">
      {label && (
        <label className="text-sm font-medium text-gray-200 flex items-center gap-2">
          {icon && <span className="text-blue-400">{icon}</span>}
          {label}
          {required && <span className="text-red-400">*</span>}
        </label>
      )}
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="flex-1 px-4 py-3 
            bg-gray-700 
            border border-gray-600 
            rounded-lg
            text-white text-sm placeholder-gray-400
            focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
            transition-colors"
        />
        <button
          type="button"
          onClick={handlePick}
          className="px-4 py-3
            bg-blue-600 hover:bg-blue-700
            text-white font-medium text-sm
            rounded-lg
            transition-colors
            flex items-center gap-2
            hover:shadow-lg"
        >
          {type === 'folder' ? <FolderIcon className="w-4 h-4" /> : <FileIcon className="w-4 h-4" />}
          Browse
        </button>
      </div>
    </div>
  );
}