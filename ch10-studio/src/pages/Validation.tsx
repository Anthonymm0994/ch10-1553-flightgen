import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { FilePicker } from '../components/FilePicker';
import ProgressLog from '../components/ProgressLog';
import { Ch10GenRunner } from '../lib/tauri';
import { CheckCircle, AlertCircle, FileSearch, Activity, Package, Wifi } from 'lucide-react';

interface TimelineEntry {
  ipts_ns: number;
  t_rel_ms: number;
  bus: string;
  rt: number;
  sa: number;
  tr: string;
  wc: number;
  status: number;
  errors: string[];
}

interface ValidationResult {
  detected?: {
    c10_tools: boolean;
    irig106: boolean;
    wireshark: boolean;
  };
  summary?: {
    packets?: number;
    channels?: string[];
  };
  ms1553?: {
    sampled?: number;
    errors?: number;
    parity_errors?: number;
  };
  notes?: string[];
}

export default function ValidationPage() {
  const [selectedFile, setSelectedFile] = useState('');
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState<string[]>([]);
  
  // Validation state
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  
  // Timeline state
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [timelineFilter, setTimelineFilter] = useState({
    rt: '',
    sa: '',
    errorsOnly: false
  });
  
  // Stats
  const [stats, setStats] = useState({
    totalMessages: 0,
    channels: [] as string[],
    reader: 'unknown'
  });

  const handleInspect = async () => {
    if (!selectedFile) {
      alert('Please select a CH10 file');
      return;
    }

    setRunning(true);
    setOutput(['Inspecting timeline...']);
    setTimeline([]);
    
    const runner = new Ch10GenRunner();
    const timelineFile = `out/timeline_${Date.now()}.jsonl`;
    
    const args = [
      'inspect',
      selectedFile,
      '--channel', 'auto',
      '--reader', 'auto',
      '--out', timelineFile,
      '--max-messages', '1000'
    ];

    runner.onStdout((line) => {
      setOutput(prev => [...prev, line]);
      
      // Parse channel detection
      if (line.includes('Found 1553 channels:')) {
        const match = line.match(/([AB])\(0x[0-9a-f]+\)=(\d+) msgs/g);
        if (match) {
          const channels = match.map(m => m.split('(')[0]);
          setStats(prev => ({ ...prev, channels }));
        }
      }
      
      // Parse reader used
      if (line.includes('Reader:')) {
        const reader = line.split('Reader:')[1].trim();
        setStats(prev => ({ ...prev, reader }));
      }
    });

    runner.onStderr((line) => {
      setOutput(prev => [...prev, `[ERROR] ${line}`]);
    });

    try {
      const exitCode = await runner.run(args);
      if (exitCode === 0) {
        setOutput(prev => [...prev, '\n[SUCCESS] Timeline extracted!']);
        
        // Read timeline file
        try {
          const response = await fetch(timelineFile);
          const text = await response.text();
          const lines = text.trim().split('\n').filter(l => l);
          const entries: TimelineEntry[] = lines.map(line => JSON.parse(line));
          setTimeline(entries);
          setStats(prev => ({ ...prev, totalMessages: entries.length }));
          setOutput(prev => [...prev, `Loaded ${entries.length} timeline entries`]);
        } catch (err) {
          setOutput(prev => [...prev, `[ERROR] Failed to load timeline: ${err}`]);
        }
      }
    } catch (error) {
      setOutput(prev => [...prev, `[ERROR] Inspection failed: ${error}`]);
    } finally {
      setRunning(false);
    }
  };

  const handleValidateExternal = async () => {
    if (!selectedFile) {
      alert('Please select a CH10 file');
      return;
    }

    setRunning(true);
    setOutput(['Running external validation...']);
    setValidationResult(null);
    
    const runner = new Ch10GenRunner();
    const outputFile = `out/validation_${Date.now()}.json`;
    
    const args = [
      'validate-external',
      selectedFile,
      '--timeout-s', '20',
      '--out', outputFile
    ];

    runner.onStdout((line) => {
      setOutput(prev => [...prev, line]);
    });

    runner.onStderr((line) => {
      setOutput(prev => [...prev, `[ERROR] ${line}`]);
    });

    try {
      const exitCode = await runner.run(args);
      setOutput(prev => [...prev, `\n[INFO] External validation completed (exit code: ${exitCode})`]);
      
      // Read validation results
      try {
        const response = await fetch(outputFile);
        const result = await response.json();
        if (result.external) {
          setValidationResult(result.external);
        }
      } catch (err) {
        setOutput(prev => [...prev, `[ERROR] Failed to load validation results: ${err}`]);
      }
    } catch (error) {
      setOutput(prev => [...prev, `[ERROR] Validation failed: ${error}`]);
    } finally {
      setRunning(false);
    }
  };

  const handleExportPCAP = async () => {
    if (!selectedFile) {
      alert('Please select a CH10 file');
      return;
    }

    setRunning(true);
    setOutput(['Exporting to PCAP...']);
    
    const runner = new Ch10GenRunner();
    const pcapFile = selectedFile.replace(/\.[^.]+$/, '.pcap');
    
    const args = [
      'export-pcap',
      selectedFile,
      '--channel', '1553A',
      '--out', pcapFile
    ];

    runner.onStdout((line) => {
      setOutput(prev => [...prev, line]);
    });

    runner.onStderr((line) => {
      setOutput(prev => [...prev, `[ERROR] ${line}`]);
    });

    try {
      const exitCode = await runner.run(args);
      if (exitCode === 0) {
        setOutput(prev => [...prev, `\n[SUCCESS] PCAP exported to: ${pcapFile}`]);
      } else if (exitCode === 3) {
        setOutput(prev => [...prev, `\n[WARNING] No messages found to export`]);
      }
    } catch (error) {
      setOutput(prev => [...prev, `[ERROR] PCAP export failed: ${error}`]);
    } finally {
      setRunning(false);
    }
  };

  const handleOpenWireshark = async () => {
    if (!selectedFile) {
      alert('Please select a CH10 file');
      return;
    }

    setRunning(true);
    setOutput(['Opening in Wireshark...']);
    
    const runner = new Ch10GenRunner();
    
    const args = [
      'open-wireshark',
      selectedFile,
      '--channel', '1553A'
    ];

    runner.onStdout((line) => {
      setOutput(prev => [...prev, line]);
    });

    runner.onStderr((line) => {
      setOutput(prev => [...prev, `[ERROR] ${line}`]);
    });

    try {
      const exitCode = await runner.run(args);
      if (exitCode === 0) {
        setOutput(prev => [...prev, '\n[SUCCESS] Opened in Wireshark']);
      } else if (exitCode === 2) {
        setOutput(prev => [...prev, '\n[WARNING] Wireshark not installed. Run: ch10gen setup-wireshark']);
      }
    } catch (error) {
      setOutput(prev => [...prev, `[ERROR] Failed to open Wireshark: ${error}`]);
    } finally {
      setRunning(false);
    }
  };

  // Filter timeline
  const filteredTimeline = timeline.filter(entry => {
    if (timelineFilter.rt && entry.rt !== parseInt(timelineFilter.rt)) return false;
    if (timelineFilter.sa && entry.sa !== parseInt(timelineFilter.sa)) return false;
    if (timelineFilter.errorsOnly && entry.errors.length === 0) return false;
    return true;
  });

  return (
    <div className="flex h-full gap-4">
      {/* Left Panel - Controls */}
      <div className="w-1/3 space-y-4 overflow-y-auto">
        {/* File Selection */}
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-xl font-bold text-gray-100 flex items-center gap-2">
              <FileSearch className="w-5 h-5" />
              CH10 File Validation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FilePicker
              label="Select CH10 File"
              value={selectedFile}
              onChange={setSelectedFile}
              placeholder="Choose file to validate..."
              filters={[{ name: 'Chapter 10', extensions: ['c10', 'ch10'] }]}
            />

            <div className="grid grid-cols-2 gap-2">
              <Button
                onClick={handleInspect}
                disabled={running || !selectedFile}
                className="bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-700"
              >
                <Activity className="w-4 h-4 mr-1" />
                Inspect Timeline
              </Button>
              
              <Button
                onClick={handleValidateExternal}
                disabled={running || !selectedFile}
                className="bg-green-600 hover:bg-green-700 text-white disabled:bg-gray-700"
              >
                <CheckCircle className="w-4 h-4 mr-1" />
                Validate External
              </Button>
              
              <Button
                onClick={handleExportPCAP}
                disabled={running || !selectedFile}
                className="bg-purple-600 hover:bg-purple-700 text-white disabled:bg-gray-700"
              >
                <Package className="w-4 h-4 mr-1" />
                Export PCAP
              </Button>
              
              <Button
                onClick={handleOpenWireshark}
                disabled={running || !selectedFile}
                className="bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-gray-700"
              >
                <Wifi className="w-4 h-4 mr-1" />
                Open Wireshark
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Validation Results */}
        {validationResult && (
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-lg text-gray-100">External Validation Results</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Tool Detection */}
              <div>
                <h4 className="text-sm font-semibold text-gray-300 mb-2">Detected Tools</h4>
                <div className="space-y-1">
                  {validationResult.detected && Object.entries(validationResult.detected).map(([tool, detected]) => (
                    <div key={tool} className="flex items-center gap-2">
                      {detected ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-gray-500" />
                      )}
                      <span className="text-sm text-gray-300">{tool}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Summary */}
              {validationResult.summary && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-300 mb-1">Summary</h4>
                  <div className="text-sm text-gray-400">
                    {validationResult.summary.packets && <div>Packets: {validationResult.summary.packets}</div>}
                    {validationResult.summary.channels && <div>Channels: {validationResult.summary.channels.join(', ')}</div>}
                  </div>
                </div>
              )}

              {/* MS1553 Stats */}
              {validationResult.ms1553 && Object.keys(validationResult.ms1553).length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-300 mb-1">MS1553</h4>
                  <div className="text-sm text-gray-400">
                    {validationResult.ms1553.sampled !== undefined && <div>Sampled: {validationResult.ms1553.sampled}</div>}
                    {validationResult.ms1553.errors !== undefined && <div>Errors: {validationResult.ms1553.errors}</div>}
                    {validationResult.ms1553.parity_errors !== undefined && <div>Parity Errors: {validationResult.ms1553.parity_errors}</div>}
                  </div>
                </div>
              )}

              {/* Notes */}
              {validationResult.notes && validationResult.notes.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-300 mb-1">Notes</h4>
                  <ul className="text-sm text-gray-400 space-y-1">
                    {validationResult.notes.map((note, i) => (
                      <li key={i} className="pl-2">• {note}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Timeline Stats */}
        {stats.totalMessages > 0 && (
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-lg text-gray-100">Timeline Statistics</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-gray-400 space-y-1">
              <div>Messages: {stats.totalMessages}</div>
              <div>Channels: {stats.channels.join(', ') || 'N/A'}</div>
              <div>Reader: {stats.reader}</div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Middle Panel - Timeline */}
      <div className="flex-1 flex flex-col">
        {timeline.length > 0 && (
          <>
            {/* Timeline Filters */}
            <Card className="bg-gray-800 border-gray-700 mb-4">
              <CardContent className="py-3">
                <div className="flex gap-4 items-center">
                  <input
                    type="number"
                    placeholder="RT Filter"
                    value={timelineFilter.rt}
                    onChange={(e) => setTimelineFilter(prev => ({ ...prev, rt: e.target.value }))}
                    className="w-24 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-gray-100 text-sm"
                  />
                  <input
                    type="number"
                    placeholder="SA Filter"
                    value={timelineFilter.sa}
                    onChange={(e) => setTimelineFilter(prev => ({ ...prev, sa: e.target.value }))}
                    className="w-24 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-gray-100 text-sm"
                  />
                  <label className="flex items-center gap-2 text-sm text-gray-300">
                    <input
                      type="checkbox"
                      checked={timelineFilter.errorsOnly}
                      onChange={(e) => setTimelineFilter(prev => ({ ...prev, errorsOnly: e.target.checked }))}
                      className="rounded bg-gray-700 border-gray-600"
                    />
                    Errors Only
                  </label>
                  <div className="ml-auto text-sm text-gray-400">
                    Showing {filteredTimeline.length} of {timeline.length} messages
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Timeline Table */}
            <Card className="bg-gray-800 border-gray-700 flex-1 overflow-hidden">
              <CardHeader>
                <CardTitle className="text-lg text-gray-100">1553 Timeline</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-auto max-h-[600px]">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-900 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left text-gray-300">Time (ms)</th>
                        <th className="px-3 py-2 text-left text-gray-300">Bus</th>
                        <th className="px-3 py-2 text-left text-gray-300">RT</th>
                        <th className="px-3 py-2 text-left text-gray-300">SA</th>
                        <th className="px-3 py-2 text-left text-gray-300">T/R</th>
                        <th className="px-3 py-2 text-left text-gray-300">WC</th>
                        <th className="px-3 py-2 text-left text-gray-300">Status</th>
                        <th className="px-3 py-2 text-left text-gray-300">Errors</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredTimeline.slice(0, 500).map((entry, i) => (
                        <tr key={i} className="border-t border-gray-700 hover:bg-gray-750">
                          <td className="px-3 py-1 text-gray-400">{entry.t_rel_ms.toFixed(2)}</td>
                          <td className="px-3 py-1 text-gray-400">{entry.bus}</td>
                          <td className="px-3 py-1 text-gray-400">{entry.rt}</td>
                          <td className="px-3 py-1 text-gray-400">{entry.sa}</td>
                          <td className="px-3 py-1 text-gray-400">{entry.tr}</td>
                          <td className="px-3 py-1 text-gray-400">{entry.wc}</td>
                          <td className="px-3 py-1 text-gray-400 font-mono text-xs">0x{entry.status.toString(16).toUpperCase()}</td>
                          <td className="px-3 py-1">
                            {entry.errors.length > 0 ? (
                              <span className="text-red-400 text-xs">{entry.errors.join(', ')}</span>
                            ) : (
                              <span className="text-green-400 text-xs">OK</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </>
        )}

        {/* Empty State */}
        {timeline.length === 0 && !running && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Select a file and click "Inspect Timeline" to view 1553 messages</p>
            </div>
          </div>
        )}
      </div>

      {/* Right Panel - Output */}
      <div className="w-1/3">
        {output.length > 0 ? (
          <Card className="bg-gray-800 border-gray-700 h-full">
            <CardHeader>
              <CardTitle className="text-lg text-gray-100">Command Output</CardTitle>
            </CardHeader>
            <CardContent className="overflow-auto max-h-[700px]">
              <ProgressLog lines={output} />
            </CardContent>
          </Card>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <p>Command output will appear here...</p>
          </div>
        )}
      </div>
    </div>
  );
}
