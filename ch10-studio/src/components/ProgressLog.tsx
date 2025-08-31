import React from 'react';

interface ProgressLogProps {
  lines: string[];
}

export default function ProgressLog({ lines }: ProgressLogProps) {
  return (
    <div className="bg-gray-900 rounded-md p-3 font-mono text-xs overflow-auto max-h-96">
      {lines.map((line, idx) => {
        let textColor = 'text-gray-300';
        if (line.includes('[ERROR]')) {
          textColor = 'text-red-400';
        } else if (line.includes('[WARNING]')) {
          textColor = 'text-yellow-400';
        } else if (line.includes('[SUCCESS]')) {
          textColor = 'text-green-400';
        } else if (line.includes('[INFO]')) {
          textColor = 'text-blue-400';
        }
        
        return (
          <div key={idx} className={`${textColor} whitespace-pre-wrap`}>
            {line}
          </div>
        );
      })}
    </div>
  );
}