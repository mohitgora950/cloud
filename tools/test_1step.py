import time
import torch
from transformers import AutoModelForCausalLM

print("Loading model...", flush=True)
t0 = time.time()
model = AutoModelForCausalLM.from_pretrained("EleutherAI/pythia-70m")
print(f"Loaded in {time.time()-t0:.2f}s", flush=True)

x = torch.randint(0, 1000, (2, 32))
print("Running forward pass with batch size 2, seq len 32...", flush=True)
t1 = time.time()
out = model(x, labels=x)
print(f"Forward completed in {time.time()-t1:.2f}s, loss = {out.loss.item():.4f}", flush=True)

print("Running backward pass...", flush=True)
t2 = time.time()
out.loss.backward()
print(f"Backward completed in {time.time()-t2:.2f}s", flush=True)

