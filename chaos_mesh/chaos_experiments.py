import random
import time

class PodKillException(Exception):
    pass

class ChaosExperimentManager:
    def __init__(self, custom_api, deployment_name, namespace):
        self.custom_api = custom_api
        self.deployment_name = deployment_name
        self.namespace = namespace
        self.active_chaos_instances = set()
        self.chaos_experiments = {
            'cpu_stress_failure': {
                'apiVersion': 'chaos-mesh.org/v1alpha1',
                'kind': 'StressChaos',
                'metadata': {
                    'name': 'cpu-stress',
                    'namespace': self.namespace
                },
                'spec': {
                    'mode': 'all',
                    'selector': {
                        'labelSelectors': {
                            'app': self.deployment_name
                        }
                    },
                    'stressors': {
                        'cpu': {
                            'workers': 4,
                            'load': 100
                        }
                    },
                    'duration': '270s'
                }
            },
            'pod_kill': {
                'apiVersion': 'chaos-mesh.org/v1alpha1',
                'kind': 'PodChaos',
                'metadata': {
                    'name': 'pod-kill',
                    'namespace': self.namespace
                },
                'spec': {
                    'action': 'pod-kill',
                    'mode': 'all',
                    'selector': {
                        'labelSelectors': {
                            'app': self.deployment_name
                        }
                    },
                }
            },
            'cpu_stress': {
                'apiVersion': 'chaos-mesh.org/v1alpha1',
                'kind': 'StressChaos',
                'metadata': {
                    'name': 'cpu-stress',
                    'namespace': self.namespace
                },
                'spec': {
                    'mode': 'all',
                    'selector': {
                        'labelSelectors': {
                            'app': self.deployment_name
                        }
                    },
                    'stressors': {
                        'cpu': {
                            'workers': 4,
                            'load': 50
                        }
                    },
                    'duration': '270s'
                }
            }
        }

    def inject_chaos(self, wait_for_pods_ready):
        if self.active_chaos_instances:
            return False
        if random.random() < 0.1:
            experiment = random.choice([
                self.chaos_experiments['cpu_stress'],
                self.chaos_experiments['cpu_stress_failure']
            ])
            try:
                self.custom_api.create_namespaced_custom_object(
                    group="chaos-mesh.org",
                    version="v1alpha1",
                    namespace=self.namespace,
                    plural="stresschaos",
                    body=experiment
                )
                self.active_chaos_instances.add(experiment['metadata']['name'])
                print(f"Injected {experiment['kind']} chaos experiment")
                if experiment == self.chaos_experiments['cpu_stress_failure']:
                    pod_kill_experiment = self.chaos_experiments['pod_kill']
                    self.custom_api.create_namespaced_custom_object(
                        group="chaos-mesh.org",
                        version="v1alpha1",
                        namespace=self.namespace,
                        plural="podchaos",
                        body=pod_kill_experiment
                    )
                    self.active_chaos_instances.add(pod_kill_experiment['metadata']['name'])
                    print("Applied pod kill experiment")
                    wait_for_pods_ready(0)
                    raise PodKillException("All pods killed")
            except PodKillException as e:
                raise e
            except Exception as e:
                print(f"Failed to inject chaos: {str(e)}")
                return False
        return False

    def cleanup_chaos(self):
        for experiment in self.chaos_experiments.values():
            kind = experiment['kind']
            name = experiment['metadata']['name']
            plural = 'podchaos' if kind == 'PodChaos' else 'stresschaos'
            try:
                self.custom_api.delete_namespaced_custom_object(
                    group="chaos-mesh.org",
                    version="v1alpha1",
                    namespace=self.namespace,
                    plural=plural,
                    name=name
                )
            except Exception:
                pass
            for _ in range(10):
                time.sleep(0.5)
                try:
                    self.custom_api.get_namespaced_custom_object(
                        group="chaos-mesh.org",
                        version="v1alpha1",
                        namespace=self.namespace,
                        plural=plural,
                        name=name
                    )
                except:
                    break
            if name in self.active_chaos_instances:
                self.active_chaos_instances.discard(name)
                print(f"Deleted {kind} chaos experiment") 