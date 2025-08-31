import React, { useState } from 'react';
import { FilePicker } from '../components/FilePicker';
import { GlassCard } from '../components/ui/glass-card';
import { Ch10GenRunner } from '../lib/tauri';
import { 
  CheckCircleIcon, XCircleIcon, AlertTriangleIcon,
  FileSearchIcon, PlayIcon, RefreshCwIcon,
  InfoIcon, PackageIcon, ClockIcon, ActivityIcon,
  DatabaseIcon, WifiIcon
} from 'lucide-react';

interface ValidationResult {
  valid: boolean;
  file_info?: {
    size: number;
    packets: number;
    duration: number;
    channels: string[];
  };
  tmats?: {
    present: boolean;
    valid: boolean;
    errors?: string[];
  };
  time_packets?: {
    count: number;
    monotonic: boolean;
    gaps?: number[];
  };
  ms1553?: {
    messages: number;
    errors: number;
    parity_errors: number;
    sync_errors: number;
    word_count_errors: number;
    rt_distribution?: { [key: string]: number };
  };
  warnings?: string[];
  errors?: string[];
}

export default function ValidationPage() {
  const [selectedFile, setSelectedFile] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [progress, setProgress] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleValidate = async () => {
    if (!selectedFile) {
      setError('Please select a CH10 file to validate');
      return;
    }

    setIsValidating(true);
    setProgress([]);
    setResult(null);
    setError(null);

    const runner = new Ch10GenRunner();
    
    runner.onStdout((line: string) => {
      setProgress(prev => [...prev, line]);
      
      // Parse validation output
      try {
        if (line.includes('{') && line.includes('}')) {
          const jsonStr = line.substring(line.indexOf('{'));
          const data = JSON.parse(jsonStr);
          if (data.validation_result) {
            setResult(data.validation_result);
          }
        }
      } catch (e) {
        // Not JSON, just progress
      }
    });

    runner.onStderr((line: string) => {
      setProgress(prev => [...prev, `ERROR: ${line}`]);
    });

    try {
      const { success, output } = await runner.runValidate(selectedFile);
      
      if (!success) {
        setError('Validation failed. Check the file format and try again.');
      } else if (!result) {
        // Parse output if we didn't get it from stdout
        parseValidationOutput(output);
      }
    } catch (err) {
      setError(`Error: ${err}`);
    } finally {
      setIsValidating(false);
    }
  };

  const parseValidationOutput = (output: string) => {
    // Simple parsing of validation output
    const lines = output.split('\n');
    const validationResult: ValidationResult = {
      valid: false,
      warnings: [],
      errors: []
    };

    for (const line of lines) {
      if (line.includes('VALID')) {
        validationResult.valid = true;
      } else if (line.includes('WARNING')) {
        validationResult.warnings?.push(line);
      } else if (line.includes('ERROR')) {
        validationResult.errors?.push(line);
      } else if (line.includes('Packets:')) {
        const match = line.match(/Packets:\s*(\d+)/);
        if (match) {
          if (!validationResult.file_info) {
            validationResult.file_info = {
              size: 0,
              packets: parseInt(match[1]),
              duration: 0,
              channels: []
            };
          }
        }
      } else if (line.includes('Messages:')) {
        const match = line.match(/Messages:\s*([\d,]+)/);
        if (match) {
          if (!validationResult.ms1553) {
            validationResult.ms1553 = {
              messages: parseInt(match[1].replace(/,/g, '')),
              errors: 0,
              parity_errors: 0,
              sync_errors: 0,
              word_count_errors: 0
            };
          }
        }
      }
    }

    setResult(validationResult);
  };

  const getStatusIcon = () => {
    if (!result) return null;
    if (result.valid) {
      return <CheckCircleIcon className="w-6 h-6 text-green-400" />;
    } else if (result.warnings && result.warnings.length > 0) {
      return <AlertTriangleIcon className="w-6 h-6 text-yellow-400" />;
    } else {
      return <XCircleIcon className="w-6 h-6 text-red-400" />;
    }
  };

  const getStatusText = () => {
    if (!result) return '';
    if (result.valid) {
      return 'Valid CH10 File';
    } else if (result.warnings && result.warnings.length > 0) {
      return 'Valid with Warnings';
    } else {
      return 'Invalid CH10 File';
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-4">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-2">
          CH10 File Validation
        </h1>
        <p className="text-gray-400">
          Validate Chapter 10 files for compliance and data integrity
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - File Selection and Actions */}
        <div className="space-y-4">
          <GlassCard className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <FileSearchIcon className="w-5 h-5 text-blue-400" />
              <h2 className="text-lg font-semibold text-white">File Selection</h2>
            </div>
            
            <FilePicker
              label="CH10 File"
              value={selectedFile}
              onChange={setSelectedFile}
              accept=".ch10,.c10"
              placeholder="Select CH10 file to validate..."
              icon={<PackageIcon className="w-4 h-4" />}
            />

            <button
              onClick={handleValidate}
              disabled={isValidating || !selectedFile}
              className={`w-full mt-4 py-3 px-4 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${
                isValidating || !selectedFile
                  ? 'bg-gray-600 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg'
              }`}
            >
              {isValidating ? (
                <>
                  <RefreshCwIcon className="w-5 h-5 animate-spin" />
                  Validating...
                </>
              ) : (
                <>
                  <PlayIcon className="w-5 h-5" />
                  Validate File
                </>
              )}
            </button>
          </GlassCard>

          {/* Quick Info */}
          <GlassCard className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <InfoIcon className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-gray-300">What's Checked</h3>
            </div>
            <ul className="space-y-1 text-xs text-gray-400">
              <li>• IRIG-106 Chapter 10 compliance</li>
              <li>• TMATS packet presence and validity</li>
              <li>• Time packet monotonicity</li>
              <li>• 1553 message integrity</li>
              <li>• Parity and sync errors</li>
              <li>• Word count validation</li>
              <li>• Channel configuration</li>
            </ul>
          </GlassCard>
        </div>

        {/* Middle Column - Validation Results */}
        <div className="lg:col-span-2 space-y-4">
          {/* Status Card */}
          {result && (
            <GlassCard className={`p-6 ${
              result.valid ? 'border-green-500/30' : 
              result.warnings?.length ? 'border-yellow-500/30' : 
              'border-red-500/30'
            }`}>
              <div className="flex items-center gap-3 mb-4">
                {getStatusIcon()}
                <div>
                  <h2 className="text-xl font-bold text-white">{getStatusText()}</h2>
                  {result.file_info && (
                    <p className="text-sm text-gray-400">
                      {result.file_info.packets} packets, {result.file_info.duration}s duration
                    </p>
                  )}
                </div>
              </div>

              {/* Detailed Results Grid */}
              <div className="grid grid-cols-2 gap-4">
                {/* TMATS Status */}
                <div className="p-3 bg-white/5 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <DatabaseIcon className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-300">TMATS</span>
                  </div>
                  {result.tmats ? (
                    <div className="text-sm">
                      <div className="flex items-center gap-2">
                        {result.tmats.present ? (
                          <CheckCircleIcon className="w-4 h-4 text-green-400" />
                        ) : (
                          <XCircleIcon className="w-4 h-4 text-red-400" />
                        )}
                        <span className="text-gray-400">
                          {result.tmats.present ? 'Present' : 'Missing'}
                        </span>
                      </div>
                      {result.tmats.valid !== undefined && (
                        <div className="flex items-center gap-2 mt-1">
                          {result.tmats.valid ? (
                            <CheckCircleIcon className="w-4 h-4 text-green-400" />
                          ) : (
                            <XCircleIcon className="w-4 h-4 text-red-400" />
                          )}
                          <span className="text-gray-400">
                            {result.tmats.valid ? 'Valid' : 'Invalid'}
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-gray-500">Not checked</span>
                  )}
                </div>

                {/* Time Packets */}
                <div className="p-3 bg-white/5 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <ClockIcon className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-300">Time Packets</span>
                  </div>
                  {result.time_packets ? (
                    <div className="text-sm">
                      <div className="text-gray-400">
                        Count: {result.time_packets.count}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        {result.time_packets.monotonic ? (
                          <CheckCircleIcon className="w-4 h-4 text-green-400" />
                        ) : (
                          <AlertTriangleIcon className="w-4 h-4 text-yellow-400" />
                        )}
                        <span className="text-gray-400">
                          {result.time_packets.monotonic ? 'Monotonic' : 'Has gaps'}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-500">Not checked</span>
                  )}
                </div>

                {/* 1553 Messages */}
                <div className="p-3 bg-white/5 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <WifiIcon className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-300">1553 Messages</span>
                  </div>
                  {result.ms1553 ? (
                    <div className="text-sm text-gray-400">
                      <div>Messages: {result.ms1553.messages.toLocaleString()}</div>
                      <div>Errors: {result.ms1553.errors}</div>
                      {result.ms1553.parity_errors > 0 && (
                        <div className="text-yellow-400">
                          Parity errors: {result.ms1553.parity_errors}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-gray-500">Not checked</span>
                  )}
                </div>

                {/* File Info */}
                <div className="p-3 bg-white/5 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <PackageIcon className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-300">File Info</span>
                  </div>
                  {result.file_info ? (
                    <div className="text-sm text-gray-400">
                      <div>Size: {(result.file_info.size / 1024).toFixed(1)} KB</div>
                      <div>Packets: {result.file_info.packets}</div>
                      <div>Channels: {result.file_info.channels.join(', ') || 'N/A'}</div>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-500">Not available</span>
                  )}
                </div>
              </div>

              {/* Warnings */}
              {result.warnings && result.warnings.length > 0 && (
                <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangleIcon className="w-4 h-4 text-yellow-400" />
                    <span className="text-sm font-medium text-yellow-400">Warnings</span>
                  </div>
                  <ul className="space-y-1">
                    {result.warnings.map((warning, i) => (
                      <li key={i} className="text-xs text-yellow-300/80">
                        • {warning}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Errors */}
              {result.errors && result.errors.length > 0 && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <XCircleIcon className="w-4 h-4 text-red-400" />
                    <span className="text-sm font-medium text-red-400">Errors</span>
                  </div>
                  <ul className="space-y-1">
                    {result.errors.map((error, i) => (
                      <li key={i} className="text-xs text-red-300/80">
                        • {error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </GlassCard>
          )}

          {/* Error Display */}
          {error && (
            <GlassCard className="p-4 border-red-500/30 bg-red-500/5">
              <div className="flex items-start gap-2">
                <XCircleIcon className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-red-400 font-semibold text-sm mb-1">Error</div>
                  <div className="text-red-300 text-sm">{error}</div>
                </div>
              </div>
            </GlassCard>
          )}

          {/* Progress Log */}
          {progress.length > 0 && (
            <GlassCard className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <ActivityIcon className="w-4 h-4 text-gray-400" />
                <h3 className="text-sm font-semibold text-gray-300">Validation Log</h3>
              </div>
              <div className="max-h-48 overflow-y-auto bg-black/20 rounded p-2">
                <div className="space-y-1">
                  {progress.slice(-20).map((line, i) => (
                    <div
                      key={i}
                      className={`text-xs font-mono ${
                        line.includes('ERROR') ? 'text-red-400' :
                        line.includes('WARNING') ? 'text-yellow-400' :
                        line.includes('VALID') ? 'text-green-400' :
                        'text-gray-400'
                      }`}
                    >
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            </GlassCard>
          )}
        </div>
      </div>
    </div>
  );
}