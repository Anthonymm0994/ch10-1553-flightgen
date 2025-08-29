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
}

export function FilePicker({
  label,
  value,
  onChange,
  type = 'file',
  filters,
  placeholder = 'Click to select...',
  icon
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
    <div className="group space-y-1.5">
      <label className="text-sm font-medium text-gray-300 flex items-center gap-1">
        {icon && <span className="text-blue-400">{icon}</span>}
        {label}
      </label>
      <div className="relative">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg opacity-0 group-hover:opacity-20 blur transition duration-300" />
        <div className="relative flex gap-3">
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="flex-1 px-3 py-2
              bg-white/5 backdrop-blur-sm
              border border-white/10 
              rounded-lg
              text-gray-100 text-sm placeholder-gray-500
              focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500/30
              transition-all duration-200
              hover:bg-white/[0.07] hover:border-white/15"
          />
          <Button
            type="button"
            onClick={handlePick}
            className="px-3 py-2
              bg-gradient-to-r from-blue-500 to-blue-600
              hover:from-blue-600 hover:to-blue-700
              text-white font-medium text-sm
              rounded-lg
              shadow-lg shadow-blue-500/20
              hover:shadow-xl hover:shadow-blue-500/25
              transition-all duration-200
              hover:scale-105 active:scale-95
              flex items-center gap-1.5"
          >
            {type === 'folder' ? <FolderIcon className="w-3.5 h-3.5" /> : <FileIcon className="w-3.5 h-3.5" />}
            Browse
          </Button>
        </div>
      </div>
    </div>
  );
}