#!/usr/bin/env python3
"""
CLI runner for PatchPilot Benchmark and Evaluation Experiments.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ml.evaluation.benchmark_harness import BenchmarkHarness

def main():
    print("Executing PatchPilot Multi-System Benchmark on held-out tasks...")
    harness = BenchmarkHarness()
    results = harness.run_all_benchmarks()

    print("\n================ BENCHMARK RESULTS SUMMARY (N=10 Held-Out Tasks) ================")
    print(f"{'System':<42} | {'Tasks Passed':<12} | {'Build Pass':<10} | {'E2E Pass':<10} | {'F1':<6} | {'Tier'}")
    print("-" * 105)
    for sys_res in results["systems"]:
        tasks_str = f"{sys_res['passed_tasks']}/{sys_res['total_tasks']}"
        print(f"{sys_res['system_name']:<42} | {tasks_str:<12} | {sys_res['build_success_rate']*100:>8.1f}% | {sys_res['end_to_end_success_rate']*100:>8.1f}% | {sys_res['localization_f1']:>5.3f} | {sys_res['execution_tier']}")

    print("\nSaved full execution metrics to datasets/processed/benchmark_results.json")
    print(f"Manifest: {results['dataset_manifest_path']}")

if __name__ == "__main__":
    main()
