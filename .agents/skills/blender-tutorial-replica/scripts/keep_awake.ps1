# Run a long render on Windows without the PC sleeping or the display turning on/off.
# Usage: powershell -ExecutionPolicy Bypass -File keep_awake.ps1 "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b scene.blend -a
param([Parameter(Mandatory = $true, Position = 0)][string]$Exe,
      [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
Add-Type -Namespace Win32 -Name Power -MemberDefinition @'
[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);
'@
# ES_CONTINUOUS | ES_SYSTEM_REQUIRED (no sleep). Display may turn off, which is what we want overnight.
[Win32.Power]::SetThreadExecutionState(0x80000000 -bor 0x00000001) | Out-Null
try {
  $p = Start-Process -FilePath $Exe -ArgumentList $Args -NoNewWindow -PassThru -Wait
  exit $p.ExitCode
} finally {
  [Win32.Power]::SetThreadExecutionState(0x80000000) | Out-Null
}
