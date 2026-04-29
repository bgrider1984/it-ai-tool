import psutil

def get_system_metrics():
    try:
        return {
            "cpu": psutil.cpu_percent(interval=0.3),
            "memory": psutil.virtual_memory().percent
        }
    except:
        return {"cpu": 0, "memory": 0}


def detect_alerts(metrics):
    alerts = []
    try:
        if metrics["cpu"] > 85:
            alerts.append("High CPU usage")
        if metrics["memory"] > 90:
            alerts.append("High memory usage")
    except:
        pass
    return alerts
