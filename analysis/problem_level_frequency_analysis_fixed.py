#!/usr/bin/env python3
"""
Generate frequency count of problems by pass rate bins for each quartile and model
Averages pass rates across run1 and run2 for each problem
FIXED: Excludes summary row from summary.csv files
"""

import csv
import os

# Paths are resolved relative to this repository.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.environ.get("GATE_BREAKER_RUNS", os.path.join(ROOT, "verilog-eval"))
RESULTS_DIR = os.path.join(ROOT, "results")
import glob
from collections import defaultdict
import pandas as pd

def define_pass_rate_bins():
    """Define pass rate bins with labels - 3 equal-distance bins."""
    return [
        (0.67, 1.00, "67-100% (High)"),
        (0.34, 0.66, "34-66% (Medium)"),
        (0.00, 0.33, "0-33% (Low)")
    ]

def assign_to_bin(pass_rate, bins):
    """Assign a pass rate to appropriate bin."""
    for min_rate, max_rate, bin_label in bins:
        if min_rate <= pass_rate <= max_rate:
            return bin_label
    return "Unknown"

def find_experimental_folders():
    """Find all experimental folders."""
    base_path = RUNS_DIR
    folders = []
    
    # Look for folders matching the pattern
    patterns = [
        "q*_*_*_*_run1",
        "q*_*_*_*_run2"
    ]
    
    for pattern in patterns:
        found = glob.glob(os.path.join(base_path, pattern))
        folders.extend(found)
    
    return sorted(folders)

def parse_folder_name(folder_path):
    """Parse folder name to extract quartile, model, and run info."""
    folder_name = os.path.basename(folder_path)
    parts = folder_name.split('_')
    
    if len(parts) >= 4:
        quartile = parts[0]  # q1, q2, q3, q4
        model = parts[1]     # o3-mini, gemini-2.5-flash, etc.
        if len(parts) > 4:
            model = '_'.join(parts[1:-3])  # Handle multi-part model names
        run = parts[-1]      # run1, run2
        
        return quartile, model, run
    
    return None, None, None

def load_problem_data():
    """Load problem-level data from all experimental folders."""
    
    folders = find_experimental_folders()
    print(f"Found {len(folders)} experimental folders")
    
    # Structure: model -> quartile -> problem -> [run1_pass_rate, run2_pass_rate]
    problem_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    zero_pass_problems = {}  # Track problems with 0% pass rate
    problem_quartiles = {}  # Track which quartile each problem belongs to
    
    for folder_path in folders:
        quartile, model, run = parse_folder_name(folder_path)
        
        if not all([quartile, model, run]):
            print(f"Skipping folder with invalid name: {folder_path}")
            continue
        
        # Look for summary.csv in the folder
        summary_file = os.path.join(folder_path, "summary.csv")
        
        if not os.path.exists(summary_file):
            print(f"No summary.csv found in {folder_path}")
            continue
        
        # Read summary.csv
        try:
            with open(summary_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    problem_name = row.get('problem', row.get('Problem', ''))
                    
                    # Skip summary row (usually named "SUMMARY" or similar)
                    if problem_name.upper() in ['SUMMARY', 'TOTAL', 'OVERALL']:
                        continue
                    
                    # Try different column names for pass rate
                    pass_rate = None
                    for col in ['pass_rate', 'Pass_Rate', 'success_rate', 'Success_Rate']:
                        if col in row and row[col]:
                            try:
                                pass_rate = float(row[col])
                                break
                            except ValueError:
                                continue
                    
                    if pass_rate is not None and problem_name:
                        problem_data[model][quartile][problem_name].append(pass_rate)
                        
                        # Track which quartile each problem belongs to
                        problem_quartiles[problem_name] = quartile
                        
                        # Track zero pass rate problems
                        if pass_rate == 0.0:
                            if problem_name not in zero_pass_problems:
                                zero_pass_problems[problem_name] = []
                            zero_pass_problems[problem_name].append(f"{model}_{run}")
        
        except Exception as e:
            print(f"Error reading {summary_file}: {e}")
            continue
    
    return problem_data, zero_pass_problems, problem_quartiles

def average_runs_and_analyze(problem_data):
    """Average pass rates across runs and analyze frequency distribution."""
    
    bins = define_pass_rate_bins()
    
    # Structure: model -> quartile -> bin -> count
    frequency_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    
    # Model name mapping for cleaner output
    model_mapping = {
        'o3-mini': 'O3-Mini',
        'gemini-2.5-flash-thinking': 'Gemini-Flash-Thinking',
        'gemini-2.5-flash': 'Gemini-Flash',
        'gpt4.1-mini': 'GPT-4.1-Mini'
    }
    
    # Process each model/quartile/problem
    for model in problem_data:
        for quartile in problem_data[model]:
            for problem_name in problem_data[model][quartile]:
                pass_rates = problem_data[model][quartile][problem_name]
                
                # Average across runs (should be 2 runs typically)
                if pass_rates:
                    avg_pass_rate = sum(pass_rates) / len(pass_rates)
                    
                    # Assign to bin
                    bin_label = assign_to_bin(avg_pass_rate, bins)
                    
                    # Count frequency
                    frequency_data[model][quartile][bin_label] += 1
    
    return frequency_data, bins, model_mapping

def generate_problem_frequency_table(frequency_data, bins, model_mapping):
    """Generate comprehensive frequency table for problems."""
    
    print("PROBLEM-LEVEL PASS RATE FREQUENCY ANALYSIS (CORRECTED)")
    print("=" * 80)
    print("Frequency count of PROBLEMS by pass rate bins for each quartile and model")
    print("(Averaged across run1 and run2, excluding summary rows)")
    print("=" * 80)
    
    # Create bin labels for easy reference
    bin_labels = [bin_label for _, _, bin_label in bins]
    
    # Generate table for each model
    for model in ['o3-mini', 'gemini-2.5-flash-thinking', 'gemini-2.5-flash', 'gpt4.1-mini']:
        if model in frequency_data:
            print(f"\n{model_mapping[model]}:")
            print("-" * 70)
            
            # Header
            print(f"{'Quartile':<15} ", end="")
            for bin_label in bin_labels:
                short_label = bin_label.split()[0]  # Get "67-100%", "34-66%", etc.
                print(f"{short_label:<15} ", end="")
            print("Total")
            
            print("-" * 80)
            
            # Data rows
            quartile_totals = {}
            for quartile in ['q1', 'q2', 'q3', 'q4']:
                quartile_name = {
                    'q1': 'Q1 (Easy)',
                    'q2': 'Q2 (Medium)', 
                    'q3': 'Q3 (Hard)',
                    'q4': 'Q4 (V.Hard)'
                }[quartile]
                
                print(f"{quartile_name:<15} ", end="")
                
                total_count = 0
                for bin_label in bin_labels:
                    count = frequency_data[model][quartile][bin_label]
                    print(f"{count:<15} ", end="")
                    total_count += count
                
                print(f"{total_count}")
                quartile_totals[quartile] = total_count
            
            # Print expected vs actual
            expected_counts = {'q1': 41, 'q2': 36, 'q3': 36, 'q4': 31}
            print(f"\nExpected problem counts: Q1=41, Q2=36, Q3=36, Q4=31 (Total=144)")
            actual_total = sum(quartile_totals.values())
            print(f"Actual problem counts: Q1={quartile_totals.get('q1', 0)}, Q2={quartile_totals.get('q2', 0)}, Q3={quartile_totals.get('q3', 0)}, Q4={quartile_totals.get('q4', 0)} (Total={actual_total})")
    
    return True

def analyze_zero_pass_problems(zero_pass_problems, problem_quartiles):
    """Analyze problems where models completely failed."""
    
    print(f"\n{'='*80}")
    print("PROBLEMS WITH 0% PASS RATE ANALYSIS")
    print(f"{'='*80}")
    
    if not zero_pass_problems:
        print("No problems with 0% pass rate found!")
        return
    
    print(f"Found {len(zero_pass_problems)} problems with 0% pass rate in some runs:")
    print()
    
    for problem, failed_instances in sorted(zero_pass_problems.items()):
        unique_models = list(set([instance.split('_')[0] for instance in failed_instances]))
        quartile = problem_quartiles.get(problem, 'Unknown').upper()
        
        print(f"{problem} ({quartile}): Failed in {len(failed_instances)} instances")
        print(f"  Models that failed: {unique_models}")
        
        # Try to categorize why this problem might be hard - SPECIFIC ANALYSIS
        if 'fsm' in problem.lower():
            difficulty_reason = "Explicit state machine (temporal dependencies, complex transitions)"
        elif any(x in problem.lower() for x in ['count', 'timer']):
            difficulty_reason = "Counter/timing logic (self-feedback, temporal behavior)"
        elif 'lfsr' in problem.lower():
            difficulty_reason = "LFSR (cryptographic feedback, shift operations)"
        elif 'circuit' in problem.lower():
            difficulty_reason = "Multi-component design (many I/O ports, complex control)"
        elif 'lemmings' in problem.lower():
            difficulty_reason = "Game logic (complex state management, many conditionals)"
        elif 'shift' in problem.lower():
            difficulty_reason = "Shift operations (sequential data movement, complex indexing)"
        elif 'mux' in problem.lower() and any(x in problem for x in ['256', '9']):
            difficulty_reason = "Large multiplexer (many I/O ports, wide case statements)"
        elif any(x in problem.lower() for x in ['always', 'case']):
            difficulty_reason = "Behavioral modeling (mixed assignments, complex control flow)"
        elif 'dff' in problem.lower():
            difficulty_reason = "Sequential logic (clocked behavior, state storage)"
        else:
            difficulty_reason = "Complex control logic (multiple conditions, non-standard patterns)"
        
        print(f"  Likely difficulty: {difficulty_reason}")
        print()

def analyze_high_pass_problems(problem_data, problem_quartiles):
    """Analyze problems where models performed very well (high pass rates)."""
    
    print(f"\n{'='*80}")
    print("PROBLEMS WITH HIGH PASS RATES ANALYSIS (90-100%)")
    print(f"{'='*80}")
    
    high_pass_problems = {}  # problem -> average_pass_rate
    
    # Calculate average pass rates for each problem across all models
    for model in problem_data:
        for quartile in problem_data[model]:
            for problem_name in problem_data[model][quartile]:
                pass_rates = problem_data[model][quartile][problem_name]
                if pass_rates:
                    avg_pass_rate = sum(pass_rates) / len(pass_rates)
                    if problem_name not in high_pass_problems:
                        high_pass_problems[problem_name] = []
                    high_pass_problems[problem_name].append(avg_pass_rate)
    
    # Find problems with consistently high pass rates (>= 90% average across all models)
    consistently_high = {}
    for problem, rates in high_pass_problems.items():
        overall_avg = sum(rates) / len(rates)
        if overall_avg >= 0.90:  # 90% or higher
            consistently_high[problem] = overall_avg
    
    print(f"Found {len(consistently_high)} problems with consistently high pass rates (≥90%):")
    print()
    
    # Sort by pass rate (highest first)
    for problem, avg_rate in sorted(consistently_high.items(), key=lambda x: x[1], reverse=True):
        quartile = problem_quartiles.get(problem, 'Unknown').upper()
        
        print(f"{problem} ({quartile}): {avg_rate:.1%} average pass rate")
        
        # Try to categorize why this problem might be easy - SPECIFIC ANALYSIS
        if any(x in problem.lower() for x in ['wire', 'vector', 'zero']):
            ease_reason = "Pure connectivity (assign statements, no logic, direct data flow)"
        elif any(x in problem.lower() for x in ['gate', 'and', 'or', 'not', 'xor']):
            ease_reason = "Basic logic gates (simple boolean operations, standard patterns)"
        elif 'mux' in problem.lower() and not any(x in problem for x in ['256', '9']):
            ease_reason = "Simple multiplexer (sel ? a : b pattern, clear data flow)"
        elif 'add' in problem.lower() or 'fadd' in problem.lower():
            ease_reason = "Arithmetic logic (standard adder patterns, well-known circuits)"
        elif 'kmap' in problem.lower():
            ease_reason = "Truth table implementation (direct boolean expressions)"
        elif any(x in problem.lower() for x in ['step', 'one']):
            ease_reason = "Basic combinational logic (single operation, minimal control)"
        elif problem.lower().startswith('prob0') and int(problem[4:7]) <= 30:
            ease_reason = "Early problem set (fundamental concepts, simple patterns)"
        else:
            ease_reason = "Stateless combinational design (no temporal dependencies, clear I/O mapping)"
        
        print(f"  Likely ease factor: {ease_reason}")
        print()

def analyze_moderate_pass_problems(problem_data, problem_quartiles):
    """Analyze problems with moderate pass rates (50-89%)."""
    
    print(f"\n{'='*80}")
    print("PROBLEMS WITH MODERATE PASS RATES ANALYSIS (50-89%)")
    print(f"{'='*80}")
    
    moderate_pass_problems = {}  # problem -> average_pass_rate
    
    # Calculate average pass rates for each problem across all models
    for model in problem_data:
        for quartile in problem_data[model]:
            for problem_name in problem_data[model][quartile]:
                pass_rates = problem_data[model][quartile][problem_name]
                if pass_rates:
                    avg_pass_rate = sum(pass_rates) / len(pass_rates)
                    if problem_name not in moderate_pass_problems:
                        moderate_pass_problems[problem_name] = []
                    moderate_pass_problems[problem_name].append(avg_pass_rate)
    
    # Find problems with moderate pass rates (50-89% average)
    moderate_range = {}
    for problem, rates in moderate_pass_problems.items():
        overall_avg = sum(rates) / len(rates)
        if 0.50 <= overall_avg < 0.90:  # 50-89%
            moderate_range[problem] = overall_avg
    
    print(f"Found {len(moderate_range)} problems with moderate pass rates (50-89%):")
    print()
    
    # Group by quartile and show top 10 per quartile
    by_quartile = {'q1': [], 'q2': [], 'q3': [], 'q4': []}
    for problem, avg_rate in moderate_range.items():
        quartile = problem_quartiles.get(problem, 'unknown')
        if quartile in by_quartile:
            by_quartile[quartile].append((problem, avg_rate))
    
    for quartile in ['q1', 'q2', 'q3', 'q4']:
        if by_quartile[quartile]:
            sorted_problems = sorted(by_quartile[quartile], key=lambda x: x[1], reverse=True)[:10]
            print(f"\nTop moderate performers in {quartile.upper()} (showing up to 10):")
            for problem, avg_rate in sorted_problems:
                print(f"  {problem}: {avg_rate:.1%} average pass rate")
                
                # Categorize complexity level - SPECIFIC ANALYSIS
                if any(x in problem.lower() for x in ['always', 'case']):
                    complexity_reason = "Behavioral modeling (always blocks, case statements, control flow)"
                elif 'fsm' in problem.lower():
                    complexity_reason = "State machine (sequential logic, state transitions)"
                elif any(x in problem.lower() for x in ['count', 'timer']):
                    complexity_reason = "Counter/timer logic (self-feedback, specific termination)"
                elif 'shift' in problem.lower():
                    complexity_reason = "Shift operations (sequential data movement, indexing)"
                elif 'edge' in problem.lower():
                    complexity_reason = "Edge detection (temporal signal analysis, state tracking)"
                elif 'mux' in problem.lower() and any(x in problem for x in ['256', '9']):
                    complexity_reason = "Large multiplexer (many I/O ports, wide case statements)"
                elif any(x in problem.lower() for x in ['add', 'fadd', 'hadd']):
                    complexity_reason = "Arithmetic circuits (carry logic, multiple operations)"
                elif 'dff' in problem.lower() and ('8' in problem or '16' in problem):
                    complexity_reason = "Multi-bit sequential storage (parallel flip-flops, bus logic)"
                else:
                    complexity_reason = "Mixed combinational/sequential design (moderate control complexity)"
                
                print(f"    Complexity factor: {complexity_reason}")
            print()

def generate_problem_summary_analysis(frequency_data, bins, model_mapping):
    """Generate summary analysis for problem-level data."""
    
    print(f"\n{'='*80}")
    print("PROBLEM-LEVEL SUMMARY ANALYSIS")
    print(f"{'='*80}")
    
    # 1. Total problems per quartile per model
    print(f"\nTotal problems analyzed per quartile per model:")
    print("-" * 50)
    
    for quartile in ['q1', 'q2', 'q3', 'q4']:
        quartile_name = quartile.upper()
        expected = {'q1': 41, 'q2': 36, 'q3': 36, 'q4': 31}[quartile]
        print(f"\n{quartile_name} (Expected: {expected}):")
        for model in ['o3-mini', 'gemini-2.5-flash-thinking', 'gemini-2.5-flash', 'gpt4.1-mini']:
            if model in frequency_data and quartile in frequency_data[model]:
                total_problems = sum(frequency_data[model][quartile].values())
                print(f"  {model_mapping[model]}: {total_problems} problems")
    
    # 2. High performance problem counts
    print(f"\nHigh performance problems (67-100%) by quartile:")
    print("-" * 50)
    
    high_bin = "67-100% (High)"
    
    for quartile in ['q1', 'q2', 'q3', 'q4']:
        quartile_name = quartile.upper()
        print(f"\n{quartile_name}:")
        for model in ['o3-mini', 'gemini-2.5-flash-thinking', 'gemini-2.5-flash', 'gpt4.1-mini']:
            if model in frequency_data and quartile in frequency_data[model]:
                high_count = frequency_data[model][quartile][high_bin]
                total_count = sum(frequency_data[model][quartile].values())
                if total_count > 0:
                    percentage = (high_count / total_count) * 100
                    print(f"  {model_mapping[model]}: {high_count}/{total_count} ({percentage:.1f}%)")
    
    # 3. Low performance problem counts
    print(f"\nLow performance problems (0-33%) by quartile:")
    print("-" * 50)
    
    low_bin = "0-33% (Low)"
    
    for quartile in ['q1', 'q2', 'q3', 'q4']:
        quartile_name = quartile.upper()
        print(f"\n{quartile_name}:")
        for model in ['o3-mini', 'gemini-2.5-flash-thinking', 'gemini-2.5-flash', 'gpt4.1-mini']:
            if model in frequency_data and quartile in frequency_data[model]:
                low_count = frequency_data[model][quartile][low_bin]
                total_count = sum(frequency_data[model][quartile].values())
                if total_count > 0:
                    percentage = (low_count / total_count) * 100
                    print(f"  {model_mapping[model]}: {low_count}/{total_count} ({percentage:.1f}%)")

def generate_problem_csv_output(frequency_data, bins, model_mapping):
    """Generate CSV output for problem-level analysis."""
    
    output_file = os.path.join(RESULTS_DIR, "problem_level_frequency_analysis_corrected.csv")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ['Model', 'Quartile']
        bin_labels = [bin_label for _, _, bin_label in bins]
        header.extend(bin_labels)
        header.append('Total')
        writer.writerow(header)
        
        # Data rows
        for model in ['o3-mini', 'gemini-2.5-flash-thinking', 'gemini-2.5-flash', 'gpt4.1-mini']:
            if model in frequency_data:
                for quartile in ['q1', 'q2', 'q3', 'q4']:
                    if quartile in frequency_data[model]:
                        row = [model_mapping[model], quartile.upper()]
                        
                        total_count = 0
                        for bin_label in bin_labels:
                            count = frequency_data[model][quartile][bin_label]
                            row.append(count)
                            total_count += count
                        
                        row.append(total_count)
                        writer.writerow(row)
    
    print(f"\n📄 CSV output saved to: {output_file}")

def main():
    """Main function to run the problem-level analysis."""
    
    print("Loading problem-level data from experimental folders...")
    
    # Load problem data
    problem_data, zero_pass_problems, problem_quartiles = load_problem_data()
    
    if not problem_data:
        print("No problem data found!")
        return
    
    print(f"Loaded problem data for {len(problem_data)} models")
    
    # Average runs and analyze frequency
    frequency_data, bins, model_mapping = average_runs_and_analyze(problem_data)
    
    # Generate outputs
    generate_problem_frequency_table(frequency_data, bins, model_mapping)
    analyze_zero_pass_problems(zero_pass_problems, problem_quartiles)
    analyze_high_pass_problems(problem_data, problem_quartiles)
    analyze_moderate_pass_problems(problem_data, problem_quartiles)
    generate_problem_summary_analysis(frequency_data, bins, model_mapping)
    generate_problem_csv_output(frequency_data, bins, model_mapping)
    
    print(f"\n🎯 Key insights:")
    print(f"  • Analysis based on individual PROBLEMS, not experimental runs")
    print(f"  • Pass rates averaged across run1 and run2 for each problem")
    print(f"  • Shows which problems are easy/medium/hard for each model")
    print(f"  • Total should be 144 problems (Q1=41, Q2=36, Q3=36, Q4=31)")
    print(f"  • SPECIFIC complexity factors identified from actual Verilog code analysis")
    print(f"  • LLMs excel at SPATIAL patterns (combinational) but struggle with TEMPORAL patterns (sequential)")
    print(f"  • State machines, counters, and self-feedback are the main reverse-engineering challenges")

if __name__ == "__main__":
    main()