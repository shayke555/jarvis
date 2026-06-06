# Run once as Administrator to register JARVIS as a Windows startup task.
# After registration, JARVIS starts automatically at every login.
$taskName = "JARVIS-bot"
$batFile   = "C:\Users\shayg\Projects\PROJECT-JARVIS\scripts\start_jarvis.bat"
$logFile   = "C:\Users\shayg\Projects\PROJECT-JARVIS\logs\jarvis.log"

$action    = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batFile`" >> `"$logFile`" 2>&1"
$trigger   = New-ScheduledTaskTrigger -AtLogon
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force

Write-Host ""
Write-Host "JARVIS registered. Starts automatically at next login."
Write-Host ""
Write-Host "Commands:"
Write-Host "  Start now:  Start-ScheduledTask -TaskName JARVIS-bot"
Write-Host "  Stop:       Stop-ScheduledTask  -TaskName JARVIS-bot"
Write-Host "  Remove:     Unregister-ScheduledTask -TaskName JARVIS-bot -Confirm:`$false"
Write-Host "  Logs:       Get-Content C:\Users\shayg\Projects\PROJECT-JARVIS\logs\jarvis.log -Tail 50"
