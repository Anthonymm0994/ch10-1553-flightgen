import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { FilePicker } from '../components/FilePicker';
import ProgressLog from '../components/ProgressLog';
import { Ch10GenRunner } from '../lib/tauri';

export default function ToolsPage() {
  // Header Patcher
  const [patchInput, setPatchInput] = useState('');
  const [patchOutput, setPatchOutput] = useState('');
  const [patchMode, setPatchMode] = useState('normalize');
  
  // Validator
  const [validateInput, setValidateInput] = useState('');
  const [useExternal, setUseExternal] = useState(false);
  
  const [output, setOutput] = useState<string[]>([]);
  const [running, setRunning] = useState(false);

  const handlePatch = async () => {
    if (!patchInput || !patchOutput) {
      alert('Please select input and output files');
      return;
    }

    setRunning(true);
    setOutput([`Patching ${patchInput}...`]);
    
    const runner = new Ch10GenRunner();
    
    const args = [
      'patch',
      '--input', patchInput,
      '--output', patchOutput,
      '--mode', patchMode
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
        setOutput(prev => [...prev, `\n[SUCCESS] File patched successfully!`]);
        setOutput(prev => [...prev, `Output: ${patchOutput}`]);
      }
    } catch (error) {
      setOutput(prev => [...prev, `[ERROR] Patch failed: ${error}`]);
    } finally {
      setRunning(false);
    }
  };

  const handleValidate = async () => {
    if (!validateInput) {
      alert('Please select a file to validate');
      return;
    }

    setRunning(true);
    setOutput([`Validating ${validateInput}...`]);
    
    const runner = new Ch10GenRunner();
    
    const args = ['validate', validateInput];
    
    if (useExternal) {
      args.push('--external');
    }

    runner.onStdout((line) => {
      setOutput(prev => [...prev, line]);
    });

    runner.onStderr((line) => {
      setOutput(prev => [...prev, `[ERROR] ${line}`]);
    });

    try {
      const exitCode = await runner.run(args);
      if (exitCode === 0) {
        setOutput(prev => [...prev, `\n[SUCCESS] Validation passed!`]);
      } else {
        setOutput(prev => [...prev, `\n[WARNING] Validation completed with issues`]);
      }
    } catch (error) {
      setOutput(prev => [...prev, `[ERROR] Validation failed: ${error}`]);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex h-full">
      {/* Left Panel - Tools */}
      <div className="w-1/2 p-4 space-y-4 overflow-y-auto border-r border-gray-700">
        {/* Header Patcher */}
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-xl font-bold text-gray-100">Header Patcher</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-400">
              Fix Chapter 10 headers for compatibility between different readers
            </p>
            
            <FilePicker
              label="Input CH10 File"
              value={patchInput}
              onChange={setPatchInput}
              placeholder="Select file to patch..."
              filters={[{ name: 'Chapter 10', extensions: ['c10', 'ch10'] }]}
            />

            <FilePicker
              label="Output File"
              value={patchOutput}
              onChange={setPatchOutput}
              placeholder="patched.c10"
              filters={[{ name: 'Chapter 10', extensions: ['c10', 'ch10'] }]}
            />

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Patch Mode</label>
              <select
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={patchMode}
                onChange={(e) => setPatchMode(e.target.value)}
                disabled={running}
              >
                <option value="normalize">Normalize (Fix to spec)</option>
                <option value="pyc10_quirks">PyChapter10 Quirks</option>
              </select>
            </div>

            <Button
              onClick={handlePatch}
              disabled={running || !patchInput || !patchOutput}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-700 disabled:text-gray-500"
            >
              {running ? 'Patching...' : 'Patch Headers'}
            </Button>
          </CardContent>
        </Card>

        {/* Validator */}
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-xl font-bold text-gray-100">CH10 Validator</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-400">
              Validate Chapter 10 files for spec compliance
            </p>
            
            <FilePicker
              label="CH10 File to Validate"
              value={validateInput}
              onChange={setValidateInput}
              placeholder="Select file to validate..."
              filters={[{ name: 'Chapter 10', extensions: ['c10', 'ch10'] }]}
            />

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={useExternal}
                onChange={(e) => setUseExternal(e.target.checked)}
                disabled={running}
                className="rounded bg-gray-700 border-gray-600 text-blue-500 focus:ring-blue-500"
              />
              <label className="text-sm text-gray-300">Use external c10-tools (if available)</label>
            </div>

            <Button
              onClick={handleValidate}
              disabled={running || !validateInput}
              className="w-full bg-green-600 hover:bg-green-700 text-white disabled:bg-gray-700 disabled:text-gray-500"
            >
              {running ? 'Validating...' : 'Validate File'}
            </Button>
          </CardContent>
        </Card>

        {/* Info Card */}
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-lg text-gray-100">About Tools</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-gray-400 space-y-2">
            <div>
              <h4 className="font-semibold text-gray-300">Header Patcher</h4>
              <p>Fixes Chapter 10 packet headers for compatibility:</p>
              <ul className="list-disc list-inside ml-2 mt-1">
                <li>Normalize: Ensures spec compliance</li>
                <li>PyC10 Quirks: Adapts for PyChapter10 library</li>
              </ul>
            </div>
            <div className="mt-3">
              <h4 className="font-semibold text-gray-300">Validator</h4>
              <p>Checks CH10 files for:</p>
              <ul className="list-disc list-inside ml-2 mt-1">
                <li>Valid packet structure</li>
                <li>IPTS monotonicity</li>
                <li>CSDW message counts</li>
                <li>Data type consistency</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Right Panel - Output */}
      <div className="w-1/2 p-4 overflow-y-auto">
        {output.length > 0 ? (
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-lg text-gray-100">Tool Output</CardTitle>
            </CardHeader>
            <CardContent>
              <ProgressLog lines={output} />
            </CardContent>
          </Card>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <p>Select a tool to begin...</p>
          </div>
        )}
      </div>
    </div>
  );
}
