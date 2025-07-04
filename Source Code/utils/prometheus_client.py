import os
from prometheus_api_client import PrometheusConnect

class PrometheusClient:
    def __init__(self, url=None):
        if url is None:
            url = os.getenv("PROMETHEUS_URL", "http://172.21.192.175:30000")
        self.prom = PrometheusConnect(url=url)

    def query(self, query):
        try:
            result = self.prom.custom_query(query)
            return float(result[0]['value'][1]) if result else 0.0
        except Exception as e:
            print(f"Prometheus query failed: {query}, error: {str(e)}")
            return 0.0
