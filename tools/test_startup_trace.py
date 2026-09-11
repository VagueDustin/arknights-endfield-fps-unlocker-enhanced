from pathlib import Path
import shutil, subprocess
root=Path.cwd()
for enabled in (False,True):
    folder=root/'build'/('trace-probe-on' if enabled else 'trace-probe-off')
    folder.mkdir(exist_ok=True)
    shutil.copy2(root/'build/native-nr-audit/startup_trace_probe.exe',folder/'probe.exe')
    (folder/'OptiScaler.ini').write_text('[FateDiagnostics]\nStartupTrace='+str(int(enabled))+'\n')
    for log in folder.glob('FateEngine-startup-trace-*.log'):log.unlink()
    processes=[subprocess.Popen([str(folder/'probe.exe')],cwd=folder) for _ in range(2)]
    for process in processes:assert process.wait(timeout=15)==0
    logs=list(folder.glob('FateEngine-startup-trace-*.log'))
    assert len(logs)==2*int(enabled)
    if enabled:
        for log in logs:
            content=log.read_text()
            assert content.count('first_chance code=C0000005')==1
            assert 'process=' in content
            assert 'process_detach' in content
    print('PASS enabled='+str(enabled)+': exception reached original handler; log state correct')
