#!/usr/bin/env python
"""Evaluation runner for comparing direct vs structured generation.

This script runs both generation approaches against a SPEC.md file and
produces a comparison report including VLM-based diagram verification.

Usage:
    python run_evaluation.py                    # Uses default SPEC.md
    python run_evaluation.py --spec OTHER.md    # Uses custom spec file
    python run_evaluation.py --verbose          # Show detailed output
    python run_evaluation.py --skip-vlm         # Skip VLM verification
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_de_diagram.cli import run_from_spec
from code_de_diagram.spec_parser import parse_spec_file
from code_de_diagram.vlm_verifier import full_verification, get_vlm_model_info
from code_de_diagram.config import get_current_config, get_model_config, get_vlm_model_config


async def run_evaluation(spec_path: str, output_base: str, verbose: bool = False, skip_vlm: bool = False) -> dict:
    """Run both solutions and compare results."""

    spec_path = Path(spec_path)
    output_base = Path(output_base)

    # Parse spec for VLM verification
    ground_truth_spec = parse_spec_file(spec_path)

    # Get model configuration
    model_config = get_model_config()
    vlm_config = get_vlm_model_config()

    print("\n" + "=" * 70)
    print("  CODE.DE.DIAGRAM EVALUATION SUITE")
    print("=" * 70)
    print(f"\nSpec file: {spec_path}")
    print(f"Output base: {output_base}")
    print(f"Started: {datetime.now().isoformat()}")

    # Display model configuration
    print("\n" + "-" * 70)
    print("  MODEL CONFIGURATION")
    print("-" * 70)
    print(f"\n{'Task':<25} {'Provider':<12} {'Model':<30}")
    print("-" * 70)
    print(f"{'Generation (LLM)':<25} {model_config.provider.value:<12} {model_config.model:<30}")
    if not skip_vlm:
        print(f"{'Verification (VLM)':<25} {vlm_config.provider.value:<12} {vlm_config.model:<30}")

    results = {
        "spec_file": str(spec_path),
        "timestamp": datetime.now().isoformat(),
        "model_config": {
            "generation": {
                "provider": model_config.provider.value,
                "model": model_config.model,
                "full_name": model_config.full_name,
            },
            "vlm": {
                "provider": vlm_config.provider.value,
                "model": vlm_config.model,
                "full_name": vlm_config.full_name,
            } if not skip_vlm else None,
        },
        "solutions": {},
    }

    # Run direct solution
    print("\n" + "-" * 70)
    print("  SOLUTION A: DIRECT GENERATION")
    print("-" * 70)

    direct_output = output_base / "direct"
    direct_results = await run_from_spec(str(spec_path), str(direct_output), "direct")
    results["solutions"]["direct"] = direct_results

    # Run structured solution
    print("\n" + "-" * 70)
    print("  SOLUTION B: STRUCTURED GENERATION")
    print("-" * 70)

    structured_output = output_base / "structured"
    structured_results = await run_from_spec(str(spec_path), str(structured_output), "structured")
    results["solutions"]["structured"] = structured_results

    # Run VLM verification on generated diagrams
    if not skip_vlm:
        print("\n" + "-" * 70)
        print("  VLM DIAGRAM VERIFICATION")
        print("-" * 70)
        vlm_info = get_vlm_model_info()
        print(f"\n  Using: {vlm_info['provider']}/{vlm_info['model']}")

        results["vlm_verification"] = {}

        for solution_name in ["direct", "structured"]:
            sol = results["solutions"][solution_name]
            diagram_path = sol.get("diagram_path")

            if diagram_path and Path(diagram_path).exists():
                print(f"\n  Verifying {solution_name} diagram...")
                try:
                    vlm_result = await full_verification(diagram_path, ground_truth_spec)
                    results["vlm_verification"][solution_name] = vlm_result

                    if vlm_result.get("verification"):
                        v = vlm_result["verification"]
                        print(f"    VLM Accuracy Score: {v.get('accuracy_score', 0):.1%}")
                        print(f"    Nodes matched: {len(v.get('node_matches', []))}")
                        print(f"    Nodes missing: {len(v.get('node_missing', []))}")
                        if v.get("issues"):
                            print(f"    Issues: {v['issues'][:2]}...")
                    elif vlm_result.get("error"):
                        print(f"    Error: {vlm_result['error']}")
                except Exception as e:
                    print(f"    VLM verification failed: {e}")
                    results["vlm_verification"][solution_name] = {"error": str(e)}
            else:
                print(f"\n  Skipping {solution_name} - no diagram generated")
                results["vlm_verification"][solution_name] = {"error": "No diagram generated"}

    # Generate comparison report
    print("\n" + "=" * 70)
    print("  EVALUATION REPORT")
    print("=" * 70)

    ground_truth = direct_results.get("ground_truth", {})
    print(f"\n📋 Ground Truth (from SPEC.md):")
    print(f"   Nodes: {ground_truth.get('nodes', 'N/A')}")
    print(f"   Edges: {ground_truth.get('edges', 'N/A')}")
    print(f"   Clusters: {ground_truth.get('clusters', 'N/A')}")

    print(f"\n📊 Results Comparison:")
    print(f"{'Metric':<25} {'Direct':<15} {'Structured':<15} {'Ground Truth':<15}")
    print("-" * 70)

    for metric in ["nodes", "edges", "clusters"]:
        gt_val = ground_truth.get(metric, "N/A")
        direct_val = direct_results.get("generated", {}).get(metric, "N/A")
        struct_val = structured_results.get("generated", {}).get(metric, "N/A")
        print(f"{metric.capitalize():<25} {direct_val:<15} {struct_val:<15} {gt_val:<15}")

    print()
    print(f"{'Execution Success':<25} {direct_results.get('success', False):<15} {structured_results.get('success', False):<15}")
    print(f"{'Execution Time (s)':<25} {direct_results.get('execution_time', 0):.2f}{'':>9} {structured_results.get('execution_time', 0):.2f}")

    # Accuracy metrics
    print(f"\n📈 Accuracy Metrics:")
    for solution_name in ["direct", "structured"]:
        sol = results["solutions"][solution_name]
        acc = sol.get("accuracy", {})
        if acc:
            print(f"\n   {solution_name.upper()}:")
            print(f"     Node Accuracy:    {acc.get('node_ratio', 0):.1%}")
            print(f"     Edge Accuracy:    {acc.get('edge_ratio', 0):.1%}")
            print(f"     Cluster Accuracy: {acc.get('cluster_ratio', 0):.1%}")

    # Errors
    print(f"\n⚠️  Errors:")
    for solution_name in ["direct", "structured"]:
        errors = results["solutions"][solution_name].get("errors", [])
        if errors:
            print(f"   {solution_name.upper()}: {errors}")
        else:
            print(f"   {solution_name.upper()}: None")

    # Output files
    print(f"\n📁 Generated Files:")
    for solution_name in ["direct", "structured"]:
        sol = results["solutions"][solution_name]
        print(f"\n   {solution_name.upper()}:")
        if sol.get("code_path"):
            print(f"     Code: {sol['code_path']}")
        if sol.get("spec_path"):
            print(f"     Spec: {sol['spec_path']}")
        if sol.get("diagram_path"):
            print(f"     Diagram: {sol['diagram_path']}")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    # Model provenance table
    print(f"\n🤖 Model Provenance:")
    print(f"{'Task':<25} {'Provider':<12} {'Model':<30}")
    print("-" * 70)
    print(f"{'Generation (LLM)':<25} {model_config.provider.value:<12} {model_config.model:<30}")
    if not skip_vlm:
        print(f"{'Verification (VLM)':<25} {vlm_config.provider.value:<12} {vlm_config.model:<30}")

    direct_success = direct_results.get("success", False)
    struct_success = structured_results.get("success", False)

    if direct_success and struct_success:
        print("\n✅ Both solutions generated diagrams successfully!")
    elif direct_success:
        print("\n⚠️  Only DIRECT solution succeeded")
    elif struct_success:
        print("\n⚠️  Only STRUCTURED solution succeeded")
    else:
        print("\n❌ Both solutions failed to generate diagrams")

    # Determine winner based on accuracy
    direct_acc = direct_results.get("accuracy", {})
    struct_acc = structured_results.get("accuracy", {})

    if direct_acc and struct_acc:
        direct_avg = sum(direct_acc.values()) / len(direct_acc)
        struct_avg = sum(struct_acc.values()) / len(struct_acc)

        print(f"\n   Direct average accuracy:     {direct_avg:.1%}")
        print(f"   Structured average accuracy: {struct_avg:.1%}")

        if struct_avg > direct_avg:
            print("\n   🏆 STRUCTURED approach performed better")
        elif direct_avg > struct_avg:
            print("\n   🏆 DIRECT approach performed better")
        else:
            print("\n   🤝 Both approaches performed equally")

    print("\n" + "=" * 70)

    # Save results JSON
    results_path = output_base / "evaluation_results.json"
    results_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n📄 Full results saved to: {results_path}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run evaluation comparing direct vs structured generation"
    )
    parser.add_argument(
        "--spec",
        type=str,
        default=str(Path(__file__).parent / "SPEC.md"),
        help="Path to SPEC.md file (default: example/SPEC.md)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=str(Path(__file__).parent / "output"),
        help="Output directory (default: example/output)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output"
    )
    parser.add_argument(
        "--skip-vlm",
        action="store_true",
        help="Skip VLM-based diagram verification"
    )
    args = parser.parse_args()

    if not Path(args.spec).exists():
        print(f"Error: Spec file not found: {args.spec}", file=sys.stderr)
        sys.exit(1)

    results = asyncio.run(run_evaluation(args.spec, args.output, args.verbose, args.skip_vlm))

    # Exit with error if both solutions failed
    both_failed = (
        not results["solutions"]["direct"].get("success", False) and
        not results["solutions"]["structured"].get("success", False)
    )
    sys.exit(1 if both_failed else 0)


if __name__ == "__main__":
    main()
