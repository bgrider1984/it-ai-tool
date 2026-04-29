import subprocess
import platform

OS = platform.system()

def run_cmd(command):
    try:
        if OS == "Windows":
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=10
            )
        else:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
        return result.stdout.strip()[:800] or "No output"
    except Exception as e:
        return f"Command failed: {str(e)}"


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
        "command": "echo CPU check not supported on this OS",
        "verify": "echo CPU verify not supported"
    }
}


def run_fix(fix_id):
    try:
        action = FIX_MAP.get(fix_id)
        if not action:
            return {"error": "Unknown fix"}

        return {
            "fix": fix_id,
            "label": action["label"],
            "output": run_cmd(action["command"])
        }
    except Exception as e:
        return {"error": str(e)}


def verify_fix(fix_id):
    try:
        action = FIX_MAP.get(fix_id)
        if not action:
            return {"error": "Unknown fix"}

        return {
            "fix": fix_id,
            "verification": run_cmd(action["verify"])
        }
    except Exception as e:
        return {"error": str(e)}
