import os
import zipfile

source_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
zip_filename = '230101056.zip'
zip_path = os.path.join(source_dir, zip_filename)
zip_parent_path = os.path.join(os.path.dirname(source_dir), zip_filename)

# Exclude patterns
EXCLUDE_DIRS = {'.git', '.pytest_cache', '__pycache__', 'model_cache'}
EXCLUDE_EXTS = {'.pyc', '.safetensors', '.bin', '.pt', '.pth'}

print(f"Creating submission zip archive: {zip_filename}...")

files_added = []
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(source_dir):
        # Modify dirs in-place to avoid descending into excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file == zip_filename:
                continue
            ext = os.path.splitext(file)[1].lower()
            if ext in EXCLUDE_EXTS:
                continue
            
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, source_dir)
            
            zf.write(full_path, arcname=rel_path)
            files_added.append(rel_path)

# Also copy to parent directory for convenience
import shutil
shutil.copy2(zip_path, zip_parent_path)

print(f"Total files packaged: {len(files_added)}")
print(f"Archive created at: {zip_path} (Size: {os.path.getsize(zip_path)/1024/1024:.2f} MB)")
print(f"Archive copy at: {zip_parent_path}")

# Verification of critical required files
required_deliverables = [
    'report/report.pdf',
    '230101056.pdf',
    'README.md',
    'AI_USE.md',
    'Makefile',
    'service/Dockerfile',
    'service/main.py',
    'k8s/deployment.yaml',
    'network/subnets.md',
    'network/nacl.json',
    'training/config.yaml',
    'results/loadtest_stats.csv',
    'results/cleaning_counts.txt',
    'results/rollback_v1.txt',
    'results/student_validation.json'
]

print("\n--- Verifying Mandatory Deliverables in Zip ---")
with zipfile.ZipFile(zip_path, 'r') as zf:
    namelist = set(zf.namelist())
    for req in required_deliverables:
        # Check normalized path
        norm_req = req.replace('/', os.sep)
        alt_req = req.replace('\\', '/')
        present = norm_req in namelist or alt_req in namelist
        status = "FOUND [OK]" if present else "MISSING [FAIL]"
        print(f"  {req:35} : {status}")
        assert present, f"Mandatory file {req} missing in zip!"

print("\nAll mandatory deliverables successfully verified in 230101056.zip!")

