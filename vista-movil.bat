@echo off
REM Vista del iPhone en vivo: levanta Vite (modo dev, puerto 5174) si hace falta y abre una ventana
REM sin barras pegada a la derecha de la pantalla. Warp/VS Code se quedan a la izquierda.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$p=5174; if(-not (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)){ Start-Process cmd -WindowStyle Hidden -WorkingDirectory '%~dp0frontend' -ArgumentList '/c','npx vite --port 5174 --strictPort'; for($i=0;$i -lt 30 -and -not (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue);$i++){Start-Sleep 1} };" ^
 "Add-Type -AssemblyName System.Windows.Forms; $a=[Windows.Forms.Screen]::PrimaryScreen.WorkingArea; $w=[int]($a.Width*0.38); $x=$a.Right-$w;" ^
 "Start-Process msedge -ArgumentList \"--app=http://localhost:5174/dev/movil\",\"--window-size=$w,$($a.Height)\",\"--window-position=$x,$($a.Top)\",\"--user-data-dir=$env:LOCALAPPDATA\multitec-vista-movil\""
