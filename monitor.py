import psutil
import time

def get_system_metrics():
    return {
        "cpu": psutil.cpu_percent(interval=0.5),
        "memory": psutil.virtual_memory().percent,
        "network_sent": psutil.net_io_counters().bytes_sent,
        "network_recv": psutil.net_io_counters().bytes_recv
    }


def detect_alerts(metrics):
    alerts = []

    if metrics["cpu"] > 85:
        alerts.append("High CPU usage detected")

    if metrics["memory"] > 90:
        alerts.append("High memory usage detected")

    return alerts
