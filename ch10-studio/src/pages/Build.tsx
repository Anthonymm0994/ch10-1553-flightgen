import React, { useState } from 'react';
import { FilePicker } from '../components/FilePicker';
import { GlassCard } from '../components/ui/glass-card';
import { Ch10GenRunner } from '../lib/tauri';
import { loadJsonReport, parseProgress } from '../lib/parse';
import { PlayIcon, CheckCircleIcon, XCircleIcon, FileCodeIcon, DatabaseIcon, PackageIcon, Sparkles, Zap, Activity } from 'lucide-react';

export function Build() {
  const [scenario, setScenario] = useState('');
  const [icd, setIcd] = useState('');
  const [output, setOutput] = useState('output.c10');
  const [writer, setWriter] = useState<'irig106' | 'pyc10'>('irig106');
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    if (!scenario || !icd || !output) {
      setError('Please fill in all required fields');
      return;
    }

    setIsRunning(true);
    setProgress([]);
    setReport(null);
    setError(null);

    const runner = new Ch10GenRunner();
    
    runner.onStdout((line: string) => {
      setProgress(prev => [...prev, line]);
      const progressData = parseProgress(line);
      if (progressData) {
        // Update UI with progress
      }
    });

    let lastError = '';
    
    runner.onStderr((line: string) => {
      setProgress(prev => [...prev, `ERROR: ${line}`]);
      // Capture the actual error message
      if (line.includes('ERROR') || line.includes('Error')) {
        lastError = line;
      }
    });

    try {
      await runner.runBuild(
        { scenario, icd, output, writer },
        (data) => {
          // Progress callback
        },
        async (success, outputPath) => {
          if (success) {
            const jsonPath = outputPath.replace('.c10', '.json');
            const report = await loadJsonReport(jsonPath);
            setReport(report);
          } else {
            // Show the actual error message if we have one
            const errorMsg = lastError || 
              progress.find(line => line.includes('ERROR'))?.replace('ERROR: ', '') ||
              'Build failed. Check the logs for details.';
            setError(`Build failed: ${errorMsg}`);
          }
          setIsRunning(false);
        }
      );
    } catch (error) {
      setError(`Error: ${error}`);
      setIsRunning(false);
    }
  };

  return (
    <div className="w-full">
      {/* Header - Compact, starts right at the top */}
      <div className="text-center mb-3">
        <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
          CH10/1553 Generator
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">Generate realistic Chapter 10 files with MIL-STD-1553 flight test data</p>
      </div>

      {/* Main Content - Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Input Section */}
        <GlassCard className="p-4 h-fit">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-1 bg-blue-500/20 rounded-lg">
              <Zap className="w-4 h-4 text-blue-400" />
            </div>
            <h2 className="text-base font-semibold text-gray-100">Configuration</h2>
          </div>

          <div className="space-y-3">
            <FilePicker
              label="Scenario File"
              value={scenario}
              onChange={setScenario}
              type="file"
              filters={[{ name: 'YAML', extensions: ['yaml', 'yml'] }]}
              placeholder="Select scenario YAML..."
              icon={<FileCodeIcon className="w-3 h-3" />}
            />

            <FilePicker
              label="ICD File"
              value={icd}
              onChange={setIcd}
              type="file"
              filters={[{ name: 'YAML', extensions: ['yaml', 'yml'] }]}
              placeholder="Select ICD YAML..."
              icon={<DatabaseIcon className="w-3 h-3" />}
            />

            <FilePicker
              label="Output File"
              value={output}
              onChange={setOutput}
              type="file"
              placeholder="output.c10"
              icon={<PackageIcon className="w-3 h-3" />}
            />

            <div className="pt-1">
              <label className="text-sm font-medium text-gray-300 mb-2 block">Writer Backend</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setWriter('irig106')}
                  className={`px-3 py-2 rounded-lg font-medium text-sm transition-all duration-200 ${
                    writer === 'irig106' 
                      ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-500/20' 
                      : 'bg-white/5 text-gray-400 hover:bg-white/10 border border-white/10'
                  }`}
                >
                  <div className="flex items-center justify-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    IRIG106 (Spec)
                  </div>
                </button>
                <button
                  onClick={() => setWriter('pyc10')}
                  className={`px-3 py-2 rounded-lg font-medium text-sm transition-all duration-200 ${
                    writer === 'pyc10' 
                      ? 'bg-gradient-to-r from-purple-500 to-purple-600 text-white shadow-lg shadow-purple-500/20' 
                      : 'bg-white/5 text-gray-400 hover:bg-white/10 border border-white/10'
                  }`}
                >
                  PyChapter10
                </button>
              </div>
            </div>

            <div className="pt-2">
              <button
                onClick={handleRun}
                disabled={isRunning}
                className={`w-full py-2.5 rounded-xl font-semibold text-white transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] ${
                  isRunning 
                    ? 'bg-gray-600 cursor-not-allowed' 
                    : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 shadow-xl shadow-green-500/20'
                }`}
              >
                <div className="flex items-center justify-center gap-2">
                  {isRunning ? (
                    <>
                      <Activity className="w-4 h-4 animate-pulse" />
                      Building...
                    </>
                  ) : (
                    <>
                      <PlayIcon className="w-4 h-4" />
                      Generate CH10 File
                    </>
                  )}
                </div>
              </button>
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg animate-pulse">
                <div className="flex items-start gap-2">
                  <XCircleIcon className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="text-red-400 font-semibold text-sm mb-1">Error</div>
                    <div className="text-red-300 text-sm whitespace-pre-wrap break-words">
                      {error}
                    </div>
                    {error.includes('validation') && (
                      <div className="text-red-300/70 text-xs mt-2">
                        Tip: Check that your ICD and scenario files are valid YAML and contain all required fields.
                      </div>
                    )}
                    {error.includes('word count') && (
                      <div className="text-red-300/70 text-xs mt-2">
                        Tip: Ensure that bitfields with word_index are properly grouped and the word count matches.
                      </div>
                    )}
                    {error.includes('mask') && (
                      <div className="text-red-300/70 text-xs mt-2">
                        Tip: Check that bitfield masks and shifts don't exceed 16 bits when combined.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </GlassCard>

        {/* Output Section */}
        <GlassCard className="p-4 h-fit">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-1 bg-purple-500/20 rounded-lg">
              <Activity className="w-4 h-4 text-purple-400" />
            </div>
            <h2 className="text-base font-semibold text-gray-100">Output</h2>
          </div>

          {progress.length > 0 && (
            <div className="bg-black/30 rounded-lg p-3 mb-3 max-h-64 overflow-y-auto">
              <pre className="text-xs text-green-400 font-mono">
                {progress.slice(-20).join('\n')}
              </pre>
            </div>
          )}

          {report && (
            <div className="space-y-3">
              <div className="p-2.5 bg-green-500/10 border border-green-500/20 rounded-lg">
                <div className="flex items-center gap-2 text-green-400 mb-2">
                  <CheckCircleIcon className="w-4 h-4" />
                  <span className="font-semibold text-sm">Build Successful!</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-white/5 rounded-lg p-2">
                    <div className="text-gray-500 text-xs">File Size</div>
                    <div className="text-gray-200 font-semibold text-sm mt-0.5">
                      {report.summary?.file_size_bytes 
                        ? `${(report.summary.file_size_bytes / 1024).toFixed(1)} KB`
                        : 'N/A'}
                    </div>
                  </div>
                  <div className="bg-white/5 rounded-lg p-2">
                    <div className="text-gray-500 text-xs">Total Packets</div>
                    <div className="text-gray-200 font-semibold text-sm mt-0.5">
                      {report.summary?.total_packets || 'N/A'}
                    </div>
                  </div>
                  <div className="bg-white/5 rounded-lg p-2">
                    <div className="text-gray-500 text-xs">Messages</div>
                    <div className="text-gray-200 font-semibold text-sm mt-0.5">
                      {report.summary?.total_messages || 'N/A'}
                    </div>
                  </div>
                  <div className="bg-white/5 rounded-lg p-2">
                    <div className="text-gray-500 text-xs">Duration</div>
                    <div className="text-gray-200 font-semibold text-sm mt-0.5">
                      {report.summary?.duration_s 
                        ? `${report.summary.duration_s.toFixed(1)}s`
                        : 'N/A'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {!isRunning && !report && progress.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <Activity className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">Waiting for output...</p>
              <p className="text-xs mt-1 text-gray-600">Run a build to see results here</p>
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}