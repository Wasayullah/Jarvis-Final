# Voice listener for Jarvis-549.
# Hosts the Windows System.Speech recognizer and answers on stdin/stdout:
#   LISTEN   -> recognise one phrase, reply "RESULT:<text>::<confidence>"
#   QUIT     -> exit cleanly
# Engine is created once and reused, and recreated after a failure.

$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech

function New-Engine {
    $engine = $null
    try {
        $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
    } catch {
        try {
            $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine -ArgumentList ([System.Globalization.CultureInfo]::GetCultureInfo('en-US'))
        } catch { $engine = $null }
    }
    return $engine
}

function Configure-Engine($engine) {
    $d = New-Object System.Speech.Recognition.DictationGrammar
    $engine.LoadGrammar($d)
    $engine.EndSilenceTimeout = [TimeSpan]::FromMilliseconds(1500)
    $engine.EndSilenceTimeoutAmbiguous = [TimeSpan]::FromMilliseconds(2500)
    $engine.InitialSilenceTimeout = [TimeSpan]::FromSeconds(5)
    $engine.BabbleTimeout = [TimeSpan]::FromSeconds(5)
    $engine.SetInputToDefaultAudioDevice()
}

$src = New-Engine
if ($null -eq $src) {
    [Console]::Out.WriteLine('ERR:NO_SPEECH_ENGINE')
    [Console]::Out.Flush()
    exit 1
}
try { Configure-Engine $src } catch {
    [Console]::Out.WriteLine('ERR:NO_MIC')
    [Console]::Out.Flush()
    try { $src.Dispose() } catch {}
    exit 1
}

# handshake: proves the helper is configured and reachable
[Console]::Out.WriteLine('READY')
[Console]::Out.Flush()

while ($true) {
    $cmd = [Console]::In.ReadLine()
    if ($null -eq $cmd) { break }
    $cmd = $cmd.Trim()
    if ($cmd -eq 'QUIT') { break }
    if ($cmd -eq 'PING') {
        [Console]::Out.WriteLine('PONG')
        [Console]::Out.Flush()
        continue
    }
    if ($cmd -ne 'LISTEN') { continue }

    $r = $null
    try {
        $r = $src.Recognize()
    } catch {
        # the engine broke; rebuild it and report an empty result
        try { $src.Dispose() } catch {}
        $src = New-Engine
        if ($null -eq $src) {
            [Console]::Out.WriteLine('ERR:RESTART_FAIL')
            [Console]::Out.Flush()
            continue
        }
        try { Configure-Engine $src } catch {}
        [Console]::Out.WriteLine('RESULT::0')
        [Console]::Out.Flush()
        continue
    }

    $text = ''
    $conf = 0
    if ($null -ne $r) {
        $text = $r.Text
        $conf = $r.Confidence
        try { $r.Dispose() } catch {}
    }
    [Console]::Out.WriteLine('RESULT:' + $text + '::' + $conf)
    [Console]::Out.Flush()
}

try { $src.Dispose() } catch {}
exit 0