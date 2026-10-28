Add-Type -AssemblyName System.Speech
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scenes = Get-Content -Raw -Encoding UTF8 (Join-Path $dir 'scenes.json') | ConvertFrom-Json
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice('Microsoft Helena Desktop')
$synth.Rate = -1
$synth.Volume = 100
foreach ($scene in $scenes) {
  $path = Join-Path $dir ("wav\" + $scene.id + ".wav")
  $synth.SetOutputToWaveFile($path)
  $synth.Speak($scene.text)
  $synth.SetOutputToNull()
  "{0}: {1:N1} KB" -f $scene.id, ((Get-Item $path).Length / 1KB)
}
