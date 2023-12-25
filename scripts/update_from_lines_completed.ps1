$LinesCompleted = Get-Content .\prompts\lines_completed.txt
$LinesCompleted = [int]$LinesCompleted
Get-Content .\prompts\tacspeak_readyornot_base.txt | Select-Object -Skip $LinesCompleted | Out-File .\prompts\tacspeak_readyornot.txt -Force
