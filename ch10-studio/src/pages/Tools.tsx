import React, { useState } from 'react';
import { FilePicker } from '../components/FilePicker';
import { GlassCard } from '../components/ui/glass-card';
import { Ch10GenRunner } from '../lib/tauri';
import { 
  PlayIcon, RefreshCwIcon, CheckCircleIcon, XCircleIcon,
  FileCodeIcon, PackageIcon, ArrowRightIcon, DownloadIcon,
  FileTextIcon, FileJsonIcon, DatabaseIcon, ActivityIcon,
  InfoIcon, CopyIcon, SaveIcon
} from 'lucide-react';

interface Tool {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

const tools: Tool[] = [
  {
    id: 'inspector',
    name: 'CH10 Inspector',
    description: 'Extract timeline and analyze 1553 messages',
    icon: <FileTextIcon className="w-5 h-5" />
  },
  {
    id: 'export',
    name: 'Export to PCAP',
    description: 'Convert CH10 to Wireshark PCAP format',
    icon: <FileJsonIcon className="w-5 h-5" />
  },
  {
    id: 'converter',
    name: 'XML to YAML',
    description: 'Convert XML message definitions to YAML ICDs',
    icon: <ArrowRightIcon className="w-5 h-5" />
  },
  {
    id: 'generator',
    name: 'Test ICD Generator',
    description: 'Generate large test ICDs for performance testing',
    icon: <DatabaseIcon className="w-5 h-5" />
  }
];

export default function ToolsPage() {
  const [selectedTool, setSelectedTool] = useState('inspector');
  const [inputFile, setInputFile] = useState('');
  const [outputFile, setOutputFile] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Tool-specific options
  const [inspectorOptions, setInspectorOptions] = useState({
    channel: 'auto',
    reader: 'auto',
    maxMessages: 1000
  });

  const [exportOptions, setExportOptions] = useState({
    format: 'pcap',
    includeTimestamps: true
  });

  const [generatorOptions, setGeneratorOptions] = useState({
    messageCount: 100,
    wordsPerMessage: 10,
    complexity: 'mixed'
  });

  const handleRun = async () => {
    if (!inputFile && selectedTool !== 'generator') {
      setError('Please select an input file');
      return;
    }

    if (!outputFile) {
      setError('Please specify an output file');
      return;
    }

    setIsRunning(true);
    setProgress([]);
    setResult(null);
    setError(null);

    const runner = new Ch10GenRunner();
    
    runner.onStdout((line: string) => {
      setProgress(prev => [...prev, line]);
    });

    runner.onStderr((line: string) => {
      setProgress(prev => [...prev, `ERROR: ${line}`]);
    });

    try {
      let args: string[] = [];

      switch (selectedTool) {
        case 'inspector':
          args = [
            'inspect',
            inputFile,
            '--channel', inspectorOptions.channel,
            '--reader', inspectorOptions.reader,
            '--out', outputFile,
            '--max-messages', inspectorOptions.maxMessages.toString()
          ];
          break;

        case 'export':
          args = [
            'export',
            inputFile,
            '--format', exportOptions.format,
            '--out', outputFile
          ];
          if (exportOptions.includeTimestamps) {
            args.push('--timestamps');
          }
          break;

        case 'converter':
          // This would need a separate implementation for XML conversion
          setError('XML to YAML conversion requires the command-line tool');
          setIsRunning(false);
          return;

        case 'generator':
          // Generate test ICD
          const testIcd = generateTestICD(generatorOptions);
          // Write to file (would need file system access)
          setResult({ generated: true, lines: testIcd.split('\n').length });
          setIsRunning(false);
          return;
      }

      const exitCode = await runner.run(args);
      
      if (exitCode === 0) {
        setResult({ success: true });
        setProgress(prev => [...prev, '✅ Operation completed successfully']);
      } else {
        setError('Operation failed. Check the logs for details.');
      }
    } catch (err) {
      setError(`Error: ${err}`);
    } finally {
      setIsRunning(false);
    }
  };

  const generateTestICD = (options: any): string => {
    // Simple test ICD generation
    const messages = [];
    for (let i = 0; i < options.messageCount; i++) {
      const words = [];
      for (let j = 0; j < options.wordsPerMessage; j++) {
        words.push(`    - name: word_${j}
      encode: u16
      const: 0`);
      }
      
      messages.push(`  - name: Message_${i}
    rate_hz: ${Math.floor(Math.random() * 50) + 1}
    rt: ${(i % 31) + 1}
    tr: BC2RT
    sa: ${(i % 30) + 1}
    wc: ${options.wordsPerMessage}
    words:
${words.join('\n')}`);
    }

    return `name: test_icd_generated
bus: B
description: Generated test ICD with ${options.messageCount} messages

messages:
${messages.join('\n')}`;
  };

  const getToolContent = () => {
    switch (selectedTool) {
      case 'inspector':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Channel Selection
              </label>
              <select
                value={inspectorOptions.channel}
                onChange={(e) => setInspectorOptions({...inspectorOptions, channel: e.target.value})}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="auto">Auto-detect</option>
                <option value="1553A">1553 Channel A</option>
                <option value="1553B">1553 Channel B</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Reader Backend
              </label>
              <select
                value={inspectorOptions.reader}
                onChange={(e) => setInspectorOptions({...inspectorOptions, reader: e.target.value})}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="auto">Auto-select</option>
                <option value="wire">Wire Format</option>
                <option value="pychapter10">PyChapter10</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Max Messages
              </label>
              <input
                type="number"
                value={inspectorOptions.maxMessages}
                onChange={(e) => setInspectorOptions({...inspectorOptions, maxMessages: parseInt(e.target.value)})}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500"
                min="1"
                max="100000"
              />
            </div>
          </div>
        );

      case 'export':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Export Format
              </label>
              <select
                value={exportOptions.format}
                onChange={(e) => setExportOptions({...exportOptions, format: e.target.value})}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="pcap">PCAP (Wireshark)</option>
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="timestamps"
                checked={exportOptions.includeTimestamps}
                onChange={(e) => setExportOptions({...exportOptions, includeTimestamps: e.target.checked})}
                className="rounded border-gray-600 bg-white/10"
              />
              <label htmlFor="timestamps" className="text-sm text-gray-300">
                Include timestamps
              </label>
            </div>
          </div>
        );

      case 'generator':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Number of Messages
              </label>
              <input
                type="number"
                value={generatorOptions.messageCount}
                onChange={(e) => setGeneratorOptions({...generatorOptions, messageCount: parseInt(e.target.value)})}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500"
                min="1"
                max="1000"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Words per Message
              </label>
              <input
                type="number"
                value={generatorOptions.wordsPerMessage}
                onChange={(e) => setGeneratorOptions({...generatorOptions, wordsPerMessage: parseInt(e.target.value)})}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500"
                min="1"
                max="32"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Complexity
              </label>
              <select
                value={generatorOptions.complexity}
                onChange={(e) => setGeneratorOptions({...generatorOptions, complexity: e.target.value})}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="simple">Simple (no bitfields)</option>
                <option value="mixed">Mixed (some bitfields)</option>
                <option value="complex">Complex (many bitfields)</option>
              </select>
            </div>
          </div>
        );

      default:
        return (
          <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <div className="flex items-start gap-2">
              <InfoIcon className="w-4 h-4 text-blue-400 mt-0.5" />
              <div className="text-sm text-gray-300">
                This tool requires the command-line interface.
                Please use the terminal to run this operation.
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-4">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-2">
          CH10 Tools
        </h1>
        <p className="text-gray-400">
          Utilities for working with Chapter 10 files and ICDs
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tool Selection */}
        <div className="space-y-4">
          <GlassCard className="p-4">
            <h2 className="text-lg font-semibold text-white mb-3">Select Tool</h2>
            <div className="space-y-2">
              {tools.map((tool) => (
                <button
                  key={tool.id}
                  onClick={() => setSelectedTool(tool.id)}
                  className={`w-full p-3 rounded-lg transition-all flex items-start gap-3 ${
                    selectedTool === tool.id
                      ? 'bg-blue-500/20 border border-blue-500/40'
                      : 'bg-white/5 border border-white/10 hover:bg-white/10'
                  }`}
                >
                  <div className={`p-1.5 rounded ${
                    selectedTool === tool.id ? 'bg-blue-500/30' : 'bg-white/10'
                  }`}>
                    {tool.icon}
                  </div>
                  <div className="text-left flex-1">
                    <div className={`font-medium ${
                      selectedTool === tool.id ? 'text-white' : 'text-gray-300'
                    }`}>
                      {tool.name}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {tool.description}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </GlassCard>
        </div>

        {/* Tool Configuration */}
        <div className="lg:col-span-2 space-y-4">
          <GlassCard className="p-6">
            <div className="flex items-center gap-2 mb-4">
              {tools.find(t => t.id === selectedTool)?.icon}
              <h2 className="text-lg font-semibold text-white">
                {tools.find(t => t.id === selectedTool)?.name}
              </h2>
            </div>

            <div className="space-y-4">
              {/* Input File */}
              {selectedTool !== 'generator' && (
                <FilePicker
                  label="Input File"
                  value={inputFile}
                  onChange={setInputFile}
                  accept={selectedTool === 'converter' ? '.xml' : '.ch10,.c10'}
                  placeholder={`Select ${selectedTool === 'converter' ? 'XML' : 'CH10'} file...`}
                  icon={<PackageIcon className="w-4 h-4" />}
                />
              )}

              {/* Output File */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Output File
                </label>
                <input
                  type="text"
                  value={outputFile}
                  onChange={(e) => setOutputFile(e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  placeholder={
                    selectedTool === 'inspector' ? 'timeline.jsonl' :
                    selectedTool === 'export' ? 'output.pcap' :
                    selectedTool === 'converter' ? 'converted.yaml' :
                    'test_icd.yaml'
                  }
                />
              </div>

              {/* Tool-specific options */}
              {getToolContent()}

              {/* Run Button */}
              <button
                onClick={handleRun}
                disabled={isRunning}
                className={`w-full py-3 px-4 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${
                  isRunning
                    ? 'bg-gray-600 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg'
                }`}
              >
                {isRunning ? (
                  <>
                    <RefreshCwIcon className="w-5 h-5 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <PlayIcon className="w-5 h-5" />
                    Run Tool
                  </>
                )}
              </button>
            </div>
          </GlassCard>

          {/* Results */}
          {result && (
            <GlassCard className="p-4 border-green-500/30 bg-green-500/5">
              <div className="flex items-start gap-2">
                <CheckCircleIcon className="w-5 h-5 text-green-400" />
                <div>
                  <div className="text-green-400 font-semibold">Success!</div>
                  <div className="text-sm text-gray-300 mt-1">
                    {result.generated && `Generated ICD with ${result.lines} lines`}
                    {result.success && `Output saved to ${outputFile}`}
                  </div>
                </div>
              </div>
            </GlassCard>
          )}

          {/* Error */}
          {error && (
            <GlassCard className="p-4 border-red-500/30 bg-red-500/5">
              <div className="flex items-start gap-2">
                <XCircleIcon className="w-5 h-5 text-red-400" />
                <div>
                  <div className="text-red-400 font-semibold">Error</div>
                  <div className="text-sm text-red-300 mt-1">{error}</div>
                </div>
              </div>
            </GlassCard>
          )}

          {/* Progress Log */}
          {progress.length > 0 && (
            <GlassCard className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <ActivityIcon className="w-4 h-4 text-gray-400" />
                <h3 className="text-sm font-semibold text-gray-300">Progress</h3>
              </div>
              <div className="max-h-48 overflow-y-auto bg-black/20 rounded p-2">
                <div className="space-y-1">
                  {progress.slice(-20).map((line, i) => (
                    <div
                      key={i}
                      className={`text-xs font-mono ${
                        line.includes('ERROR') ? 'text-red-400' :
                        line.includes('SUCCESS') || line.includes('✅') ? 'text-green-400' :
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