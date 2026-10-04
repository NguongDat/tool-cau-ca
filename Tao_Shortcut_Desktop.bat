@echo off
echo Dang tao Shortcut tren Desktop...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Roblox Fishing Master Auto.lnk')); $s.TargetPath = '%~dp0run_tool.bat'; $s.WorkingDirectory = '%~dp0'; $s.Save()"
echo Da tao Shortcut thanh cong tren man hinh Desktop!
timeout /t 2 >nul
