import subprocess
import platform


def run_powershell(command):
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True
        )
        return result.stdout[:500]
    except Exception as e:
        return str(e)


# 🔐 SAFE COMMAND WHITELIST
SAFE_COMMANDS = {
    "network_check": "Get-NetAdapter | Select Name, Status",
    "ip_config": "ipconfig",
    "usb_devices": "Get-PnpDevice -Class USB",
    "disk_space": "Get-PSDrive -PSProvider FileSystem",
    "cpu_usage": "Get-Process | Sort CPU -Descending | Select -First 5",
}


# 🔧 SAFE AUTO FIXES
SAFE_FIXES = {
    "reset_network": "ipconfig /release; ipconfig /renew",
    "flush_dns": "ipconfig /flushdns",
    "restart_adapter": "Disable-NetAdapter -Name '*' -Confirm:$false; Start-Sleep -Seconds 2; Enable-NetAdapter -Name '*' -Confirm:$false",
}


def run_tool(name, input_data=None, allow_fix=False):

    # 🧠 Diagnostic tools
    if name in SAFE_COMMANDS:
        return {
            "tool": name,
            "output": run_powershell(SAFE_COMMANDS[name])
        }

    # 🔧 Auto-fix tools (restricted)
    if allow_fix and name in SAFE_FIXES:
        return {
            "tool": name,
            "output": run_powershell(SAFE_FIXES[name]),
            "type": "fix_executed"
        }

    return {
        "tool": name,
        "error": "Tool not allowed or unknown"
    }
