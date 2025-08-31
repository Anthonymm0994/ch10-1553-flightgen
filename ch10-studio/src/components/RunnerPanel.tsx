import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Play, StopCircle, Settings2 } from 'lucide-react';
import { Ch10GenOptions, Ch10GenRunner } from '@/lib/tauri';

interface RunnerPanelProps {
  options: Ch10GenOptions;
  onOptionsChange: (options: Partial<Ch10GenOptions>) => void;
  onRun: () => void;
  onStop: () => void;
  isRunning: boolean;
}

export function RunnerPanel({
  options,
  onOptionsChange,
  onRun,
  onStop,
  isRunning
}: RunnerPanelProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Build Configuration</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <Settings2 className="w-4 h-4 mr-1" />
            Advanced
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">Writer Backend</label>
            <select
              value={options.writer}
              onChange={(e) => onOptionsChange({ writer: e.target.value as 'irig106' | 'pyc10' })}
              className="w-full mt-1 px-3 py-2 border rounded-md"
              disabled={isRunning}
            >
              <option value="irig106">irig106 (Spec-compliant)</option>
              <option value="pyc10">pyc10 (Compatibility)</option>
            </select>
          </div>

          <div>
            <label className="text-sm font-medium">Duration Override (s)</label>
            <input
              type="number"
              value={options.duration || ''}
              onChange={(e) => onOptionsChange({ duration: e.target.value ? parseFloat(e.target.value) : undefined })}
              placeholder="Use scenario default"
              className="w-full mt-1 px-3 py-2 border rounded-md"
              disabled={isRunning}
            />
          </div>
        </div>

        {showAdvanced && (
          <div className="grid grid-cols-2 gap-4 pt-4 border-t">
            <div>
              <label className="text-sm font-medium">Flush Interval (ms)</label>
              <input
                type="number"
                value={options.flushMs || 100}
                onChange={(e) => onOptionsChange({ flushMs: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 border rounded-md"
                disabled={isRunning}
              />
            </div>

            <div>
              <label className="text-sm font-medium">Max Packet Bytes</label>
              <input
                type="number"
                value={options.maxPacketBytes || 65536}
                onChange={(e) => onOptionsChange({ maxPacketBytes: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 border rounded-md"
                disabled={isRunning}
              />
            </div>

            <div>
              <label className="text-sm font-medium">Timeout (s)</label>
              <input
                type="number"
                value={options.timeoutS || ''}
                onChange={(e) => onOptionsChange({ timeoutS: e.target.value ? parseFloat(e.target.value) : undefined })}
                placeholder="No timeout"
                className="w-full mt-1 px-3 py-2 border rounded-md"
                disabled={isRunning}
              />
            </div>

            <div>
              <label className="text-sm font-medium">Progress Interval</label>
              <input
                type="number"
                value={options.progressInterval || 100}
                onChange={(e) => onOptionsChange({ progressInterval: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 border rounded-md"
                disabled={isRunning}
              />
            </div>
          </div>
        )}

        <div className="flex items-center gap-4 pt-4">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="export-decoded"
              checked={options.exportDecoded || false}
              onChange={(e) => onOptionsChange({ exportDecoded: e.target.checked })}
              disabled={isRunning}
            />
            <label htmlFor="export-decoded" className="text-sm">
              Export decoded CSV
            </label>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="verbose"
              checked={options.verbose || false}
              onChange={(e) => onOptionsChange({ verbose: e.target.checked })}
              disabled={isRunning}
            />
            <label htmlFor="verbose" className="text-sm">
              Verbose output
            </label>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          {isRunning ? (
            <Button
              variant="destructive"
              onClick={onStop}
            >
              <StopCircle className="w-4 h-4 mr-2" />
              Stop
            </Button>
          ) : (
            <Button
              onClick={onRun}
              disabled={!options.scenario || !options.icd || !options.output}
            >
              <Play className="w-4 h-4 mr-2" />
              Run Build
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
