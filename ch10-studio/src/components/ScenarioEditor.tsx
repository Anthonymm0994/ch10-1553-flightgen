import React, { useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Button } from './ui/button';
import { Save, FileText } from 'lucide-react';
import { writeFile } from '@/lib/tauri';

interface ScenarioEditorProps {
  value: string;
  onChange: (value: string) => void;
  filePath?: string;
  title?: string;
}

const DEFAULT_SCENARIO = `# Demo Scenario
name: "Demo Mission"
start_time_utc: "2025-01-15T14:00:00Z"
duration_s: 10
seed: 42

profile:
  base_altitude_ft: 15000
  segments:
    - type: cruise
      ias_kt: 350
      hold_s: 10

bus:
  packet_bytes_target: 8192
`;

export function ScenarioEditor({
  value,
  onChange,
  filePath,
  title = "Scenario"
}: ScenarioEditorProps) {
  const editorRef = useRef<any>(null);

  const handleSave = async () => {
    if (filePath) {
      try {
        await writeFile(filePath, value);
        console.log('Saved to', filePath);
      } catch (error) {
        console.error('Error saving file:', error);
      }
    }
  };

  const handleApplyDefault = () => {
    onChange(DEFAULT_SCENARIO);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-2 border-b">
        <h3 className="font-medium">{title}</h3>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleApplyDefault}
          >
            <FileText className="w-4 h-4 mr-1" />
            Default
          </Button>
          {filePath && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleSave}
            >
              <Save className="w-4 h-4 mr-1" />
              Save
            </Button>
          )}
        </div>
      </div>
      <div className="flex-1">
        <Editor
          height="100%"
          defaultLanguage="yaml"
          value={value}
          onChange={(val) => onChange(val || '')}
          onMount={(editor) => {
            editorRef.current = editor;
          }}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            theme: 'vs-dark'
          }}
        />
      </div>
    </div>
  );
}
