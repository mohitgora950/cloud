import subprocess
import time
import threading
import requests
import json

stop_traffic = False
stats = {'total': 0, 'success': 0, 'fail': 0, 'latencies': []}
log_lines = []

def traffic_worker():
    session = requests.Session()
    while not stop_traffic:
        t0 = time.time()
        try:
            r = session.post('http://localhost:8080/parse', json={'text': 'pod failure recovery test traffic'}, timeout=10)
            dur = time.time() - t0
            stats['total'] += 1
            if r.status_code == 200:
                stats['success'] += 1
                stats['latencies'].append(dur)
            else:
                stats['fail'] += 1
        except Exception:
            stats['total'] += 1
            stats['fail'] += 1
        time.sleep(0.05)

print('Starting background continuous traffic thread...')
threads = [threading.Thread(target=traffic_worker, daemon=True) for _ in range(2)]
for th in threads:
    th.start()
time.sleep(3)

# Find an active pod to terminate
res = subprocess.run(['kubectl', 'get', 'pods', '-n', 'app', '-o', 'json'], capture_output=True, text=True, check=True)
data = json.loads(res.stdout)
active_pods = [p['metadata']['name'] for p in data.get('items', []) if not p.get('metadata', {}).get('deletionTimestamp')]

if not active_pods:
    raise RuntimeError('No active pods found in app namespace.')

target_pod = active_pods[0]
print(f'Simulating pod failure: deleting {target_pod}...')
t_start = time.time()
subprocess.run(['kubectl', 'delete', 'pod', target_pod, '-n', 'app', '--grace-period=0', '--force'], capture_output=True, text=True)

# Wait for recovery back to full replicas
recovered = False
recovery_dur = 0.0
while time.time() - t_start < 60:
    time.sleep(2)
    p_res = subprocess.run(['kubectl', 'get', 'pods', '-n', 'app', '-o', 'json'], capture_output=True, text=True)
    if p_res.returncode != 0:
        continue
    p_data = json.loads(p_res.stdout)
    p_items = p_data.get('items', [])
    ready_count = 0
    all_ready = True
    for p in p_items:
        if p.get('metadata', {}).get('deletionTimestamp'):
            all_ready = False
            continue
        statuses = p.get('status', {}).get('containerStatuses', [])
        if statuses and all(s.get('ready', False) for s in statuses):
            ready_count += 1
        else:
            all_ready = False
    if all_ready and ready_count >= 2:
        recovery_dur = time.time() - t_start
        print(f'Cluster recovered in {recovery_dur:.2f}s ({ready_count} replicas Ready).')
        recovered = True
        break

time.sleep(3)
stop_traffic = True
for th in threads:
    th.join(timeout=5)

fail_rate = (stats['fail'] / max(stats['total'], 1)) * 100
avg_lat = (sum(stats['latencies']) / len(stats['latencies'])) if stats['latencies'] else 0.0
status_text = "PASSED (High Availability Resiliency Verified)" if fail_rate < 2.0 and recovered else "FAILED"

log_lines.append('=== Kubernetes Pod Failure Recovery Reliability Test ===')
log_lines.append('Deployment: command-parser in namespace app')
log_lines.append(f'Target Pod Terminated: {target_pod}')
log_lines.append(f'Time to Full Replica Recovery: {recovery_dur:.2f} seconds')
log_lines.append(f'Total Traffic Requests Sent: {stats["total"]}')
log_lines.append(f'Successful Requests (HTTP 200): {stats["success"]}')
log_lines.append(f'Failed Requests: {stats["fail"]}')
log_lines.append(f'Measured Failure Rate: {fail_rate:.2f}% (Threshold: < 2.0%)')
log_lines.append(f'Average Request Latency: {avg_lat*1000:.2f} ms')
log_lines.append(f'Status: {status_text}')

print(f'\nTotal: {stats["total"]}, Success: {stats["success"]}, Fail: {stats["fail"]}, Failure Rate: {fail_rate:.2f}%')
with open('results/pod_recovery.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(log_lines) + '\n')
print('Evidence saved to results/pod_recovery.txt')

