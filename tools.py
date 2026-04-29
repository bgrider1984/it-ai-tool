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


# 🔧 FIX ACTION MAP (SAFE)
FIX_ACTIONS = {
    "Flush DNS": {
        "command": "ipconfig /flushdns",
        "verify": "ipconfig"
    },
    "Reset Network": {
        "command": "ipconfig /release; ipconfig /renew",
        "verify": "ipconfig"
    },
    "Check CPU Load": {
        "command": "Get-Process | Sort CPU -Descending | Select -First 5",
        "verify": "Get-Process | Sort CPU -Descending | Select -First 5"
    }
}


def run_fix(fix_name):
    if fix_name not in FIX_ACTIONS:
        return {"error": "Fix not supported"}

    action = FIX_ACTIONS[fix_name]

    result = run_cmd(action["command"])

    return {
        "fix": fix_name,
        "output": result
    }


def verify_fix(fix_name):
    if fix_name not in FIX_ACTIONS:
        return {"error": "Verification not supported"}

    verify_cmd = FIX_ACTIONS[fix_name]["verify"]

    result = run_cmd(verify_cmd)

    return {
        "fix": fix_name,
        "verification": result
    }
