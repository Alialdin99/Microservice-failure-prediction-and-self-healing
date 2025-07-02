import time
from kubernetes import client, config

class K8sClient:
    def __init__(self, deployment_name, namespace):
        config.load_kube_config()
        self.k8s_api = client.AppsV1Api()
        self.deployment_name = deployment_name
        self.namespace = namespace

    def read_deployment(self):
        return self.k8s_api.read_namespaced_deployment(
            name=self.deployment_name, namespace=self.namespace
        )

    def scale_deployment(self, replicas):
        deployment = self.read_deployment()
        deployment.spec.replicas = int(replicas)
        self.k8s_api.patch_namespaced_deployment(
            name=self.deployment_name,
            namespace=self.namespace,
            body=deployment
        )
        self.wait_for_pods_ready(replicas)
        time.sleep(3)

    def wait_for_pods_ready(self, expected_replicas, timeout=60):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                deployment = self.read_deployment()
                if deployment.spec.replicas != expected_replicas:
                    print(f"Deployment replicas mismatch: expected {expected_replicas}, got {deployment.spec.replicas}")
                    return False
                if (deployment.status.ready_replicas == expected_replicas and 
                    deployment.status.available_replicas == expected_replicas):
                    print(f"All {expected_replicas} pods are ready")
                    return True
                print(f"Waiting for pods: {deployment.status.ready_replicas}/{expected_replicas} ready")
                time.sleep(2)
            except Exception as e:
                print(f"Error checking pod readiness: {str(e)}")
                time.sleep(2)
        print(f"Timeout waiting for {expected_replicas} pods to be ready")
        return False

    def get_current_replicas(self):
        deployment = self.read_deployment()
        return deployment.spec.replicas

    def get_annotations(self):
        deployment = self.read_deployment()
        return deployment.metadata.annotations or {} 