import React from 'react';

interface SummaryCardsProps {
  summary: any;
}

export default function SummaryCards({ summary }: SummaryCardsProps) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-1">File Size</h3>
        <p className="text-2xl font-bold text-gray-100">
          {(summary.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
        </p>
      </div>
      
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-1">Total Packets</h3>
        <p className="text-2xl font-bold text-gray-100">
          {summary.total_packets?.toLocaleString() || '0'}
        </p>
      </div>
      
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-1">Total Messages</h3>
        <p className="text-2xl font-bold text-gray-100">
          {summary.total_messages?.toLocaleString() || '0'}
        </p>
      </div>
      
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-1">Duration</h3>
        <p className="text-2xl font-bold text-gray-100">
          {summary.duration_s ? `${summary.duration_s.toFixed(1)}s` : 'N/A'}
        </p>
      </div>
    </div>
  );
}