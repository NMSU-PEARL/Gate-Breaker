#!/usr/bin/env python3
"""
Script to run similarity analysis on all 32 experimental folders using improved_similarity_analysis.py
Activates the simeval conda environment and processes each folder sequentially.
"""

import os

# Paths are resolved relative to this repository.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.environ.get("GATE_BREAKER_RUNS", os.path.join(ROOT, "verilog-eval"))
RESULTS_DIR = os.path.join(ROOT, "results")
os.environ.setdefault(
    "GATE_BREAKER_REF_DIR", os.path.join(ROOT, "verilog-eval", "dataset_netlist-to-rtl"))
import subprocess
import glob
import time
from pathlib import Path

def find_experimental_folders():
    """Find all q* experimental folders."""
    base_dir = RUNS_DIR
    pattern = os.path.join(base_dir, "q[1-4]_*")
    folders = glob.glob(pattern)
    folders = [f for f in folders if os.path.isdir(f)]
    return sorted(folders)

def run_similarity_analysis_with_conda(folder_path, output_dir, methods="ast,cfg"):
    """Run similarity analysis for a specific folder with conda environment activation."""
    
    # Script path
    script_path = os.path.join(ROOT, "simeval", "improved_similarity_analysis.py")
    folder_name = os.path.basename(folder_path)
    
    # Create bash command that activates conda and runs the script
    bash_command = f"""
    # Try multiple conda initialization paths
    if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
    elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
    elif [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
        source "/opt/conda/etc/profile.d/conda.sh"
    else
        echo "Warning: Could not find conda initialization script"
    fi
    
    # Activate simeval environment
    conda activate simeval
    
    # Check if activation was successful
    if [ "$CONDA_DEFAULT_ENV" = "simeval" ]; then
        echo "✓ Successfully activated simeval environment"
    else
        echo "⚠️ Warning: May not be in simeval environment (current: $CONDA_DEFAULT_ENV)"
    fi
    
    # Run the similarity analysis
    echo "Running similarity analysis for {folder_name}..."
    python3 "{script_path}" \\
        --build-dir "{folder_path}" \\
        --methods {methods} \\
        --output-dir "{output_dir}" \\
        --parallel 25 \\
        --timeout 120
    
    echo "Completed analysis for {folder_name} (exit code: $?)"
    """
    
    print(f"🔄 Processing {folder_name}...")
    
    try:
        # Run the bash command
        result = subprocess.run(
            ["bash", "-c", bash_command],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout per folder
        )
        
        print(f"📊 Output for {folder_name}:")
        if result.stdout:
            # Print last 10 lines of stdout
            stdout_lines = result.stdout.strip().split('\n')
            print("STDOUT (last 10 lines):")
            for line in stdout_lines[-10:]:
                print(f"  {line}")
        
        if result.stderr:
            print("STDERR:")
            stderr_lines = result.stderr.strip().split('\n')
            for line in stderr_lines[-5:]:  # Last 5 lines of stderr
                print(f"  {line}")
        
        if result.returncode == 0:
            print(f"✅ Successfully completed {folder_name}")
            return True
        else:
            print(f"❌ Failed {folder_name} (exit code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ Timeout for {folder_name} after 30 minutes")
        return False
    except Exception as e:
        print(f"💥 Exception for {folder_name}: {e}")
        return False

def main():
    print("🚀 SIMILARITY ANALYSIS FOR ALL EXPERIMENTAL FOLDERS")
    print("=" * 70)
    
    # Setup
    base_dir = RUNS_DIR
    output_dir = os.path.join(RESULTS_DIR, "similarity_results")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")
    
    # Find experimental folders
    folders = find_experimental_folders()
    print(f"📊 Found {len(folders)} experimental folders:")
    
    # Filter out the current working directory if it's in the list
    current_dir = os.getcwd()
    folders = [f for f in folders if os.path.abspath(f) != current_dir]
    
    for i, folder in enumerate(folders, 1):
        print(f"  {i:2d}. {os.path.basename(folder)}")
    
    # Configuration
    methods = "ast,cfg"  # Start with AST and CFG (faster than netlist)
    print(f"🔧 Similarity methods: {methods}")
    print(f"🔧 Parallel processes: 25")
    print(f"🔧 Timeout per analysis: 120s")
    
    # Process folders
    print(f"\n🎯 Processing {len(folders)} folders...")
    print("=" * 70)
    
    start_time = time.time()
    successful = 0
    failed = 0
    
    for i, folder in enumerate(folders, 1):
        print(f"\n[{i}/{len(folders)}] 📂 {os.path.basename(folder)}")
        print("-" * 50)
        
        folder_start = time.time()
        success = run_similarity_analysis_with_conda(folder, output_dir, methods)
        folder_time = time.time() - folder_start
        
        if success:
            successful += 1
            print(f"✅ Completed in {folder_time:.1f}s")
        else:
            failed += 1
            print(f"❌ Failed after {folder_time:.1f}s")
        
        print(f"📈 Progress: {successful} successful, {failed} failed")
        
        # Brief pause between folders
        time.sleep(2)
    
    # Final summary
    total_time = time.time() - start_time
    
    print(f"\n{'=' * 70}")
    print("🏁 FINAL SUMMARY")
    print(f"{'=' * 70}")
    print(f"📊 Total folders: {len(folders)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success rate: {successful/len(folders)*100:.1f}%")
    print(f"⏱️ Total time: {total_time/60:.1f} minutes")
    
    # Check output files
    output_files = glob.glob(os.path.join(output_dir, "similarity_*.csv"))
    print(f"\n📄 Generated {len(output_files)} output files:")
    for output_file in sorted(output_files):
        file_size = os.path.getsize(output_file)
        print(f"  📄 {os.path.basename(output_file)} ({file_size:,} bytes)")
    
    print(f"\n📁 Results saved in: {output_dir}")
    
    # Next steps
    print(f"\n🎯 Next steps:")
    print(f"  1. Check individual CSV files for similarity scores")
    print(f"  2. Use extract_similarity_metrics.py to aggregate results")
    print(f"  3. Analyze similarity patterns across models and quartiles")
    print(f"  4. Compare similarity scores with Pass@K performance metrics")

if __name__ == "__main__":
    main()