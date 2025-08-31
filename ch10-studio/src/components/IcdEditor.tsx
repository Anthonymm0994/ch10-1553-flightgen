import React, { useRef } from 'react';
import Editor from '@monaco-editor/react';
import { Button } from './ui/button';
import { Save, FileText } from 'lucide-react';
import { writeFile } from '@/lib/tauri';

interface IcdEditorProps {
  value: string;
  onChange: (value: string) => void;
  filePath?: string;
  title?: string;
}

const DEFAULT_ICD = `# Demo ICD
bus: A
messages:
  - name: NAV_DATA
    rate_hz: 20
    rt: 10
    tr: RT2BC
    sa: 1
    wc: 16
    words:
      - { name: latitude,  encode: float32_split, word_order: lsw_msw, src: flight.lat_deg }
      - { name: longitude, encode: float32_split, word_order: lsw_msw, src: flight.lon_deg }
      - { name: altitude,  encode: bnr16, scale: 0.25, src: flight.altitude_ft }
      - { name: heading,   encode: bnr16, scale: 0.1, src: flight.heading_deg }
      - { name: pitch,     encode: bnr16, scale: 0.1, src: flight.pitch_deg }
      - { name: roll,      encode: bnr16, scale: 0.1, src: flight.roll_deg }
      - { name: ias,       encode: u16, src: flight.ias_kt }
      - { name: reserved0, encode: u16, const: 0 }
      - { name: reserved1, encode: u16, const: 0 }
      - { name: reserved2, encode: u16, const: 0 }
      - { name: reserved3, encode: u16, const: 0 }
      - { name: reserved4, encode: u16, const: 0 }
      - { name: reserved5, encode: u16, const: 0 }
      - { name: reserved6, encode: u16, const: 0 }
`;

export function IcdEditor({
  value,
  onChange,
  filePath,
  title = "ICD"
}: IcdEditorProps) {
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
    onChange(DEFAULT_ICD);
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
