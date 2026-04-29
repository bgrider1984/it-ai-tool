import subprocess

def run_powershell(command):
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()[:800]
    except Exception as e:
        return str(e)


SAFE_COMMANDS = {
    "network_check": "Get-NetAdapter | Format-Table",
    "ip_config": "ipconfig",
    "usb_devices": "Get-PnpDevice -Class USB",
    "disk_space": "Get-PSDrive -PSProvider FileSystem",
    "cpu_usage": "Get-Process | Sort CPU -Descending | Select -First 5"
}

SAFE_FIXES = {
    "flush_dns": "ipconfig /flushdns",
    "reset_network": "ipconfig /release; ipconfig /renew"
}


def run_tool(name, allow_fix=False):
    if name in SAFE_COMMANDS:
        return {
            "type": "diagnostic",
            "tool": name,
            "output": run_powershell(SAFE_COMMANDS[name])
        }

    if allow_fix and name in SAFE_FIXES:
        return {
            "type": "fix",
            "tool": name,
            "output": run_powershell(SAFE_FIXES[name])
        }

    return {"error": "Unknown or not allowed"}
