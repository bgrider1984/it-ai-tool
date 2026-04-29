import subprocess
import platform

OS = platform.system()


def run_cmd(command):
    try:
        if OS == "Windows":
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True
            )
        else:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True
            )

        return result.stdout.strip()[:800]
    except Exception as e:
        return str(e)


FIX_MAP = {
    "flush_dns": {
        "label": "Flush DNS Cache",
        "command": "ipconfig /flushdns",
        "verify": "ipconfig"
    },
    "reset_network": {
        "label": "Reset Network Adapter",
        "command": "ipconfig /release; ipconfig /renew",
        "verify": "ipconfig"
    },
    "check_cpu": {
        "label": "Check CPU Usage",
        "command": "Get-Process | Sort CPU -Descending | Select -First 5",
        "verify": "Get-Process | Sort CPU -Descending | Select -First 5"
    }
}


def get_fix_details(fix_id):
    return FIX_MAP.get(fix_id)


def run_fix(fix_id):
    if fix_id not in FIX_MAP:
        return {"error": "Invalid fix"}

    action = FIX_MAP[fix_id]
    return {
        "fix": fix_id,
        "label": action["label"],
        "output": run_cmd(action["command"])
    }


def verify_fix(fix_id):
    if fix_id not in FIX_MAP:
        return {"error": "Invalid fix"}

    action = FIX_MAP[fix_id]
    return {
        "fix": fix_id,
        "verification": run_cmd(action["verify"])
    }
