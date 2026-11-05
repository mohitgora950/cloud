import subprocess
import time
import threading
import requests

stop_traffic = False
stats = {'total': 0, 'success': 0, 'fail': 0, 'latencies': []}
log_lines = []

def traffic_worker():
    session = requests.Session()
    while not stop_traffic:
        t0 = time.time()
        try:
            r = session.post('http://localhost:8080/parse', json={'text': 'rolling update test traffic'}, timeout=10)
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
time.sleep(2)

print('Executing kubectl rollout restart deployment/command-parser -n app...')
t_start = time.time()
subprocess.run(['kubectl', 'rollout', 'restart', 'deployment/command-parser', '-n', 'app'], check=True)

print('Waiting for rollout status deployment/command-parser...')
res = subprocess.run(['kubectl', 'rollout', 'status', 'deployment/command-parser', '-n', 'app', '--timeout=120s'], capture_output=True, text=True)
rollout_dur = time.time() - t_start
print(f'Rollout completed in {rollout_dur:.2f}s: {res.stdout.strip()}')

# Let traffic run for 3 more seconds
time.sleep(3)
stop_traffic = True
for th in threads:
    th.join(timeout=5)

fail_rate = (stats['fail'] / max(stats['total'], 1)) * 100
avg_lat = (sum(stats['latencies']) / len(stats['latencies'])) if stats['latencies'] else 0.0

status_text = "PASSED (Zero Downtime)" if fail_rate < 0.5 else "FAILED"
log_lines.append('=== Kubernetes Rolling Update Reliability Test ===')
log_lines.append('Deployment: command-parser in namespace app')
log_lines.append(f'Rollout Duration: {rollout_dur:.2f} seconds')
log_lines.append(f'Total Traffic Requests Sent: {stats["total"]}')
log_lines.append(f'Successful Requests (HTTP 200): {stats["success"]}')
log_lines.append(f'Failed Requests: {stats["fail"]}')
log_lines.append(f'Measured Failure Rate: {fail_rate:.2f}% (Threshold: < 0.5%)')
log_lines.append(f'Average Request Latency: {avg_lat*1000:.2f} ms')
log_lines.append(f'Status: {status_text}')
log_lines.append(f'Rollout Output: {res.stdout.strip()}')

print(f'\nTotal: {stats["total"]}, Success: {stats["success"]}, Fail: {stats["fail"]}, Failure Rate: {fail_rate:.2f}%')
with open('results/rolling_update.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(log_lines) + '\n')
print('Evidence saved to results/rolling_update.txt')
