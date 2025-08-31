import React, { useState } from 'react';
import { Ch10GenRunner, createTempScenario, pickFile } from '../lib/tauri';

export function Build() {
  const [icd, setIcd] = useState('');
  const [output, setOutput] = useState('output.ch10');
  const [duration, setDuration] = useState('60');
  const [writer, setWriter] = useState<'irig106' | 'pyc10'>('pyc10');
  const [dataMode, setDataMode] = useState<'flight' | 'random' | 'scenario'>('random');
  const [scenario, setScenario] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState<'idle' | 'running' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [outputLog, setOutputLog] = useState<string[]>([]);

  const handleSelectICD = async () => {
    const file = await pickFile([
      { name: 'YAML', extensions: ['yaml', 'yml'] },
      { name: 'All', extensions: ['*'] }
    ]);
    if (file) setIcd(file as string);
  };

  const handleSelectScenario = async () => {
    const file = await pickFile([
      { name: 'YAML', extensions: ['yaml', 'yml'] },
      { name: 'All', extensions: ['*'] }
    ]);
    if (file) setScenario(file as string);
  };

  const generateDefaultScenario = () => {
    const baseScenario: any = {
      name: 'Generated Scenario',
      duration_s: parseInt(duration) || 60,
      start_time_utc: new Date().toISOString(),
      bus: {
        utilization_percent: 50,
        packet_bytes_target: 65536
      }
    };

    if (dataMode === 'random') {
      baseScenario.defaults = {
        data_mode: 'random',
        default_config: {
          distribution: 'uniform'
        }
      };
    } else if (dataMode === 'flight') {
      baseScenario.defaults = {
        data_mode: 'flight',
        default_config: {}
      };
      baseScenario.profile = {
        base_altitude_ft: 10000,
        segments: [
          {
            type: 'climb',
            to_altitude_ft: 15000,
            ias_kt: 280,
            vs_fpm: 1500,
            duration_s: Math.min(30, parseInt(duration) / 2)
          },
          {
            type: 'cruise',
            ias_kt: 320,
            hold_s: Math.max(30, parseInt(duration) / 2)
          }
        ]
      };
    }

    return baseScenario;
  };

  const handleGenerate = async () => {
    if (!icd) {
      setStatus('error');
      setMessage('Please select an ICD file');
      return;
    }

    setIsRunning(true);
    setStatus('running');
    setMessage('Generating CH10 file...');
    setOutputLog([]);

    const runner = new Ch10GenRunner();
    const logs: string[] = [];

    runner.onStdout((line: string) => {
      logs.push(line);
      setOutputLog([...logs]);
    });

    runner.onStderr((line: string) => {
      logs.push(`ERROR: ${line}`);
      setOutputLog([...logs]);
    });

    try {
      let scenarioToUse = scenario;
      if (!scenario && dataMode !== 'scenario') {
        const tempScenario = generateDefaultScenario();
        scenarioToUse = await createTempScenario(tempScenario);
      }

      await runner.runBuild(
        { 
          scenario: scenarioToUse, 
          icd, 
          output, 
          writer,
          duration: parseInt(duration),
          verbose: true
        },
        (data) => {
          if (data.status) {
            logs.push(data.status);
            setOutputLog([...logs]);
          }
        },
        async (success, outputText) => {
          if (success) {
            setStatus('success');
            setMessage(`Generated ${output} successfully`);
          } else {
            setStatus('error');
            const errorLog = logs.join('\n');
            if (errorLog.includes('FileNotFoundError')) {
              setMessage('File not found. Check your file paths.');
            } else if (errorLog.includes('YAMLError')) {
              setMessage('Invalid YAML format in configuration files.');
            } else if (!logs.length) {
              setMessage('Failed to run generator. Check that ch10gen.exe is in the binaries folder.');
            } else {
              setMessage('Generation failed. See output log for details.');
            }
          }
          setIsRunning(false);
        }
      );
    } catch (error) {
      setStatus('error');
      setMessage(`Error: ${error}`);
      setIsRunning(false);
    }
  };

  return (
    <div style={{ 
      padding: '32px',
      maxWidth: '1200px',
      margin: '0 auto',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      <h1 style={{ 
        fontSize: '32px',
        fontWeight: '600',
        marginBottom: '32px',
        color: '#ffffff'
      }}>
        CH10 File Generator
      </h1>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '32px' }}>
        {/* Main Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Configuration */}
          <div style={{
            background: '#1a1a1a',
            borderRadius: '8px',
            padding: '24px',
            border: '1px solid #333'
          }}>
            <h2 style={{ fontSize: '18px', fontWeight: '500', marginBottom: '20px', color: '#ffffff' }}>
              Configuration
            </h2>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#999' }}>
                  ICD Definition File
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    value={icd}
                    onChange={(e) => setIcd(e.target.value)}
                    placeholder="Select ICD file..."
                    style={{
                      flex: 1,
                      padding: '10px 12px',
                      background: '#0a0a0a',
                      border: '1px solid #333',
                      borderRadius: '4px',
                      color: '#fff',
                      fontSize: '14px'
                    }}
                  />
                  <button
                    onClick={handleSelectICD}
                    style={{
                      padding: '10px 20px',
                      background: '#333',
                      border: 'none',
                      borderRadius: '4px',
                      color: '#fff',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    Browse
                  </button>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#999' }}>
                  Output File
                </label>
                <input
                  type="text"
                  value={output}
                  onChange={(e) => setOutput(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    background: '#0a0a0a',
                    border: '1px solid #333',
                    borderRadius: '4px',
                    color: '#fff',
                    fontSize: '14px'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#999' }}>
                  Duration (seconds)
                </label>
                <input
                  type="number"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    background: '#0a0a0a',
                    border: '1px solid #333',
                    borderRadius: '4px',
                    color: '#fff',
                    fontSize: '14px'
                  }}
                />
              </div>
            </div>
          </div>

          {/* Data Mode */}
          <div style={{
            background: '#1a1a1a',
            borderRadius: '8px',
            padding: '24px',
            border: '1px solid #333'
          }}>
            <h2 style={{ fontSize: '18px', fontWeight: '500', marginBottom: '20px', color: '#ffffff' }}>
              Data Mode
            </h2>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '16px' }}>
              {(['random', 'flight', 'scenario'] as const).map(mode => (
                <button
                  key={mode}
                  onClick={() => setDataMode(mode)}
                  style={{
                    padding: '12px',
                    background: dataMode === mode ? '#0066cc' : '#0a0a0a',
                    border: '1px solid ' + (dataMode === mode ? '#0066cc' : '#333'),
                    borderRadius: '4px',
                    color: '#fff',
                    cursor: 'pointer',
                    fontSize: '14px',
                    textTransform: 'capitalize'
                  }}
                >
                  {mode === 'scenario' ? 'Custom' : mode}
                </button>
              ))}
            </div>

            {dataMode === 'scenario' && (
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#999' }}>
                  Scenario File
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    value={scenario}
                    onChange={(e) => setScenario(e.target.value)}
                    placeholder="Select scenario file..."
                    style={{
                      flex: 1,
                      padding: '10px 12px',
                      background: '#0a0a0a',
                      border: '1px solid #333',
                      borderRadius: '4px',
                      color: '#fff',
                      fontSize: '14px'
                    }}
                  />
                  <button
                    onClick={handleSelectScenario}
                    style={{
                      padding: '10px 20px',
                      background: '#333',
                      border: 'none',
                      borderRadius: '4px',
                      color: '#fff',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    Browse
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Advanced */}
          <div style={{
            background: '#1a1a1a',
            borderRadius: '8px',
            padding: '24px',
            border: '1px solid #333'
          }}>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              style={{
                background: 'none',
                border: 'none',
                color: '#999',
                cursor: 'pointer',
                fontSize: '14px',
                padding: 0,
                marginBottom: showAdvanced ? '16px' : 0
              }}
            >
              {showAdvanced ? '▼' : '▶'} Advanced Options
            </button>
            
            {showAdvanced && (
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', color: '#999' }}>
                  Writer Backend
                </label>
                <select
                  value={writer}
                  onChange={(e) => setWriter(e.target.value as 'irig106' | 'pyc10')}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    background: '#0a0a0a',
                    border: '1px solid #333',
                    borderRadius: '4px',
                    color: '#fff',
                    fontSize: '14px'
                  }}
                >
                  <option value="pyc10">PyChapter10</option>
                  <option value="irig106">IRIG-106</option>
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={isRunning}
            style={{
              padding: '16px',
              background: isRunning ? '#333' : '#0066cc',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '16px',
              fontWeight: '500',
              cursor: isRunning ? 'default' : 'pointer',
              opacity: isRunning ? 0.5 : 1
            }}
          >
            {isRunning ? 'Generating...' : 'Generate CH10 File'}
          </button>

          {/* Status */}
          {message && (
            <div style={{
              padding: '16px',
              background: status === 'error' ? '#331111' : status === 'success' ? '#113311' : '#1a1a1a',
              border: '1px solid ' + (status === 'error' ? '#663333' : status === 'success' ? '#336633' : '#333'),
              borderRadius: '8px'
            }}>
              <div style={{
                color: status === 'error' ? '#ff6666' : status === 'success' ? '#66ff66' : '#999',
                fontSize: '14px'
              }}>
                {message}
              </div>
            </div>
          )}

          {/* Output Log */}
          {outputLog.length > 0 && (
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #333',
              borderRadius: '8px',
              padding: '16px',
              maxHeight: '300px',
              overflow: 'auto'
            }}>
              <div style={{ fontSize: '12px', fontFamily: 'monospace', color: '#999' }}>
                {outputLog.slice(-20).map((line, i) => (
                  <div key={i} style={{ 
                    marginBottom: '4px',
                    color: line.includes('ERROR') ? '#ff6666' : line.includes('SUCCESS') ? '#66ff66' : '#999'
                  }}>
                    {line}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}