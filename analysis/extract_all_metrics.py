#!/usr/bin/env python3

import os

# Paths are resolved relative to this repository.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.environ.get("GATE_BREAKER_RUNS", os.path.join(ROOT, "verilog-eval"))
RESULTS_DIR = os.path.join(ROOT, "results")
import csv
import glob
from collections import defaultdict

def parse_summary_file(filepath):
    """Parse a summary.csv file and extract all available metrics."""
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('problem') == 'SUMMARY':
                    return {
                        'pass_count': int(row['pass']),
                        'total_samples': int(row['samples']),
                        'pass_rate': float(row['pass_rate']),
                        'pass_at_1': float(row['pass@1']),
                        'pass_at_5': float(row['pass@5']),
                        'pass_at_10': float(row['pass@10'])
                    }
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None

def parse_timing_file(filepath):
    """Parse a timing.txt file and extract timing information."""
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if line.startswith('make_time_seconds:'):
                    time_str = line.split(':')[1].strip()
                    return {'make_time_seconds': int(time_str)}
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None

def extract_experiment_info(folder_name):
    """Extract quartile, model, and run info from folder name."""
    parts = folder_name.split('_')
    quartile = parts[0]  # q1, q2, q3, q4
    model = parts[1]     # model name
    prompt_type = parts[2]  # cot
    shot_count = parts[3]   # shot2
    run_number = parts[4]   # run1, run2
    
    return {
        'quartile': quartile,
        'model': model,
        'prompt_type': prompt_type,
        'shot_count': shot_count,
        'run_number': run_number
    }

def main():
    print("Extracting metrics from all 32 experimental folders")
    print("=" * 60)
    
    base_dir = RUNS_DIR
    
    # Find all quartile experiment directories
    pattern = os.path.join(base_dir, "q[1-4]_*")
    all_dirs = glob.glob(pattern)
    all_dirs = [d for d in all_dirs if os.path.isdir(d)]
    all_dirs.sort()
    
    print(f"Found {len(all_dirs)} experimental folders:")
    for i, d in enumerate(all_dirs, 1):
        print(f"  {i:2d}. {os.path.basename(d)}")
    
    print(f"\nMetrics to extract from each folder:")
    print(f"  - pass_count: Number of problems that passed")
    print(f"  - total_samples: Total number of problems attempted")
    print(f"  - pass_rate: Overall pass rate (pass_count/total_samples)")
    print(f"  - pass_at_1: Pass@1 metric (probability of success in 1 attempt)")
    print(f"  - pass_at_5: Pass@5 metric (probability of success in 5 attempts)")
    print(f"  - pass_at_10: Pass@10 metric (probability of success in 10 attempts)")
    print(f"  - make_time_seconds: Total execution time in seconds")
    
    # Extract metrics from all folders
    all_results = []
    
    print(f"\nExtracting metrics...")
    print("-" * 60)
    
    for dir_path in all_dirs:
        folder_name = os.path.basename(dir_path)
        summary_file = os.path.join(dir_path, 'summary.csv')
        timing_file = os.path.join(dir_path, 'timing.txt')
        
        if os.path.exists(summary_file):
            metrics = parse_summary_file(summary_file)
            if metrics:
                # Extract experiment info
                exp_info = extract_experiment_info(folder_name)
                
                # Extract timing info if available
                timing_info = parse_timing_file(timing_file) if os.path.exists(timing_file) else {'make_time_seconds': None}
                
                # Combine experiment info with metrics and timing
                result = {**exp_info, **metrics, **timing_info}
                result['folder_name'] = folder_name
                all_results.append(result)
                
                time_str = f", Time={timing_info['make_time_seconds']}s" if timing_info['make_time_seconds'] is not None else ", Time=N/A"
                print(f"✓ {folder_name}: Pass@1={metrics['pass_at_1']:.3f}, Pass@5={metrics['pass_at_5']:.3f}, Pass@10={metrics['pass_at_10']:.3f}{time_str}")
            else:
                print(f"✗ {folder_name}: Could not parse summary.csv")
        else:
            print(f"✗ {folder_name}: No summary.csv found")
    
    # Save all results to CSV
    if all_results:
        output_file = os.path.join(RESULTS_DIR, "all_experiment_metrics.csv")
        
        fieldnames = ['folder_name', 'quartile', 'model', 'prompt_type', 'shot_count', 'run_number',
                     'pass_count', 'total_samples', 'pass_rate', 'pass_at_1', 'pass_at_5', 'pass_at_10', 'make_time_seconds']
        
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
        
        print(f"\n{'='*60}")
        print(f"SUCCESS: Extracted metrics from {len(all_results)}/{len(all_dirs)} folders")
        print(f"Results saved to: {output_file}")
        
        # Summary statistics
        models = set(r['model'] for r in all_results)
        quartiles = set(r['quartile'] for r in all_results)
        
        print(f"\nSummary:")
        print(f"  Models: {sorted(models)}")
        print(f"  Quartiles: {sorted(quartiles)}")
        print(f"  Total experiments: {len(all_results)}")
        
        # Model performance summary
        print(f"\nModel Performance Summary (averaged across all quartiles and runs):")
        model_stats = defaultdict(list)
        for result in all_results:
            model_stats[result['model']].append({
                'pass_at_1': result['pass_at_1'],
                'pass_at_5': result['pass_at_5'],
                'pass_at_10': result['pass_at_10'],
                'make_time_seconds': result['make_time_seconds']
            })
        
        for model in sorted(model_stats.keys()):
            stats = model_stats[model]
            avg_p1 = sum(s['pass_at_1'] for s in stats) / len(stats)
            avg_p5 = sum(s['pass_at_5'] for s in stats) / len(stats)
            avg_p10 = sum(s['pass_at_10'] for s in stats) / len(stats)
            
            # Calculate average time (excluding None values)
            valid_times = [s['make_time_seconds'] for s in stats if s['make_time_seconds'] is not None]
            avg_time = sum(valid_times) / len(valid_times) if valid_times else None
            time_str = f", Time={avg_time:.0f}s" if avg_time is not None else ", Time=N/A"
            
            print(f"  {model}: Pass@1={avg_p1:.3f}, Pass@5={avg_p5:.3f}, Pass@10={avg_p10:.3f}{time_str} (n={len(stats)})")
        
    else:
        print(f"\nERROR: No valid metrics extracted from any folder")

if __name__ == "__main__":
    main()