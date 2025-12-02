"""Command-line interface."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .config import print_config


async def run_direct_interactive():
    """Run direct generation interactive session."""
    from .solutions.direct import DirectGenerationAgent

    print("=" * 60)
    print("code.de.diagram - Direct LLM Code Generation")
    print("=" * 60)
    print_config()
    print("\nDescribe your architecture. Commands: quit, show, run\n")

    agent = DirectGenerationAgent()

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() == 'quit':
            break
        if user_input.lower() == 'show':
            print(agent.get_code() or "No code yet.")
            continue
        if user_input.lower() == 'run':
            success, msg = agent.execute_code()
            print(f"{'SUCCESS' if success else 'FAILED'}: {msg}")
            continue

        if agent.generated_code:
            print("Refining...")
            result = await agent.refine(user_input)
            print(f"\n{result.explanation}")
        else:
            print("Analyzing...")
            analysis = await agent.analyze(user_input)
            print(f"\n{analysis.summary}")
            print(f"Components: {', '.join(analysis.identified_components)}")

            if analysis.questions:
                print("\nQuestions:")
                for q in analysis.questions:
                    print(f"  - {q.question}")

            if analysis.ready_to_generate:
                print("\nGenerating code...")
                result = await agent.generate_code()
                print(f"\n{result.explanation}")
                print("\nType 'run' to generate diagram.")
            else:
                print(f"\nConfidence: {analysis.confidence:.0%}")


async def run_structured_interactive():
    """Run structured generation interactive session."""
    from .solutions.structured import StructuredAgent

    print("=" * 60)
    print("code.de.diagram - Structured Generation")
    print("=" * 60)
    print_config()
    print("\nDescribe your architecture. Commands: quit, spec, code, run\n")

    agent = StructuredAgent()

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() == 'quit':
            break
        if user_input.lower() == 'spec':
            print(agent.get_spec_json() or "No spec yet.")
            continue
        if user_input.lower() == 'code':
            try:
                print(agent.render_code())
            except ValueError as e:
                print(f"Error: {e}")
            continue
        if user_input.lower() == 'run':
            success, msg = agent.execute()
            print(f"{'SUCCESS' if success else 'FAILED'}: {msg}")
            continue

        if agent.current_spec:
            print("Refining...")
            result = await agent.refine_spec(user_input)
            print(f"\n{result.explanation}")
        else:
            print("Analyzing...")
            analysis = await agent.analyze(user_input)
            print(f"\n{analysis.summary}")
            print(f"Components: {', '.join(analysis.identified_components)}")
            print(f"Clusters: {', '.join(analysis.suggested_clusters)}")

            if analysis.questions:
                print("\nQuestions:")
                for q in analysis.questions:
                    print(f"  - {q.question}")

            if analysis.ready_to_generate:
                print("\nGenerating spec...")
                result = await agent.generate_spec()
                print(f"\n{result.explanation}")
                spec = result.spec
                print(f"\nSpec: {len(spec.nodes)} nodes, {len(spec.edges)} edges, {len(spec.clusters)} clusters")
                print("\nType 'run' to generate diagram.")
            else:
                print(f"\nConfidence: {analysis.confidence:.0%}")


async def run_from_spec(spec_path: str, output_dir: str, solution: str) -> dict:
    """Run generation from a SPEC.md file (non-interactive mode).

    Returns a results dict with metrics for evaluation.
    """
    from .spec_parser import parse_spec_file, spec_to_natural_language, get_expected_counts
    from .solutions.direct import DirectGenerationAgent
    from .solutions.structured import StructuredAgent
    from .renderer import render_and_execute
    import time

    spec_path = Path(spec_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"Running {solution.upper()} generation from: {spec_path.name}")
    print(f"Output directory: {output_dir}")
    print(f"{'=' * 60}")

    # Parse the spec file
    print("\n[1/4] Parsing spec file...")
    ground_truth = parse_spec_file(spec_path)
    expected = get_expected_counts(spec_path)
    natural_lang = spec_to_natural_language(ground_truth)

    print(f"  Ground truth: {len(ground_truth.nodes)} nodes, {len(ground_truth.edges)} edges, {len(ground_truth.clusters)} clusters")
    if expected["nodes"]:
        print(f"  Expected: {expected['nodes']} nodes, {expected['edges']} edges, {expected['clusters']} clusters")

    results = {
        "solution": solution,
        "spec_file": str(spec_path),
        "ground_truth": {
            "nodes": len(ground_truth.nodes),
            "edges": len(ground_truth.edges),
            "clusters": len(ground_truth.clusters),
        },
        "expected": expected,
        "generated": {},
        "success": False,
        "execution_time": 0,
        "diagram_path": None,
        "code_path": None,
        "spec_path": None,
        "errors": [],
    }

    start_time = time.time()

    try:
        if solution in ("direct", "a"):
            agent = DirectGenerationAgent(output_dir=str(output_dir))

            print("\n[2/4] Analyzing with LLM...")
            analysis = await agent.analyze(natural_lang)
            print(f"  Components found: {len(analysis.identified_components)}")
            print(f"  Ready to generate: {analysis.ready_to_generate}")

            if not analysis.ready_to_generate:
                print("  WARNING: LLM not confident, generating anyway...")

            print("\n[3/4] Generating code...")
            # Pass the full architecture description to the generator
            code_result = await agent.generate_code(architecture_description=natural_lang)
            print(f"  Explanation: {code_result.explanation[:100]}...")

            # Save generated code
            code_path = output_dir / f"{solution}_generated.py"
            code_path.write_text(agent.get_code())
            results["code_path"] = str(code_path)

            # Count components in generated code (rough)
            code = agent.get_code() or ""
            results["generated"]["nodes"] = (
                code.count("= EC2(") + code.count("= Server(") + code.count("= WAF(") +
                code.count("= ALB(") + code.count("= Nginx(") + code.count("= PostgreSQL(") +
                code.count("= S3(") + code.count("= EFS(") + code.count("= Aurora(") +
                code.count("= ElastiCache(") + code.count("= RDS(")
            )
            results["generated"]["edges"] = code.count(">>")
            results["generated"]["clusters"] = code.count("with Cluster(")

            print("\n[4/4] Executing code...")
            success, message = agent.execute_code()
            results["success"] = success
            if success:
                results["diagram_path"] = agent.get_diagram_path()
                print(f"  SUCCESS: {message}")
            else:
                results["errors"].append(message)
                print(f"  FAILED: {message}")

        else:  # structured
            agent = StructuredAgent(output_dir=str(output_dir))

            print("\n[2/4] Analyzing with LLM...")
            analysis = await agent.analyze(natural_lang)
            print(f"  Components found: {len(analysis.identified_components)}")
            print(f"  Clusters suggested: {len(analysis.suggested_clusters)}")

            if not analysis.ready_to_generate:
                print("  WARNING: LLM not confident, generating anyway...")

            print("\n[3/4] Generating spec...")
            # Pass the full architecture description to the generator
            spec_result = await agent.generate_spec(architecture_description=natural_lang)
            generated_spec = spec_result.spec
            print(f"  Generated: {len(generated_spec.nodes)} nodes, {len(generated_spec.edges)} edges, {len(generated_spec.clusters)} clusters")

            results["generated"]["nodes"] = len(generated_spec.nodes)
            results["generated"]["edges"] = len(generated_spec.edges)
            results["generated"]["clusters"] = len(generated_spec.clusters)

            # Save generated spec
            spec_out_path = output_dir / f"{solution}_generated_spec.json"
            spec_out_path.write_text(generated_spec.model_dump_json(indent=2))
            results["spec_path"] = str(spec_out_path)

            # Save generated code
            code = agent.render_code()
            code_path = output_dir / f"{solution}_generated.py"
            code_path.write_text(code)
            results["code_path"] = str(code_path)

            print("\n[4/4] Executing code...")
            success, message = agent.execute()
            results["success"] = success
            if success:
                results["diagram_path"] = agent.get_diagram_path()
                print(f"  SUCCESS: {message}")
            else:
                results["errors"].append(message)
                print(f"  FAILED: {message}")

    except Exception as e:
        results["errors"].append(str(e))
        print(f"\n  ERROR: {e}")

    results["execution_time"] = time.time() - start_time

    # Calculate accuracy metrics
    if results["generated"]:
        gt = results["ground_truth"]
        gen = results["generated"]
        results["accuracy"] = {
            "node_ratio": gen["nodes"] / gt["nodes"] if gt["nodes"] else 0,
            "edge_ratio": gen["edges"] / gt["edges"] if gt["edges"] else 0,
            "cluster_ratio": gen["clusters"] / gt["clusters"] if gt["clusters"] else 0,
        }

    print(f"\n  Execution time: {results['execution_time']:.2f}s")

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="code-de-diagram",
        description="LLM-driven architecture diagram generation"
    )
    parser.add_argument(
        "--solution", "-s",
        choices=["direct", "structured", "a", "b"],
        default="structured",
        help="Generation approach: direct (a) or structured (b)"
    )
    parser.add_argument(
        "--spec",
        type=str,
        metavar="SPEC.md",
        help="Path to SPEC.md file for non-interactive mode"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./output",
        help="Output directory for generated files"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (for scripting)"
    )
    parser.add_argument(
        "--config", "-c",
        action="store_true",
        help="Show config and exit"
    )
    args = parser.parse_args()

    if args.config:
        print_config()
        return

    # Non-interactive mode with spec file
    if args.spec:
        if not Path(args.spec).exists():
            print(f"Error: Spec file not found: {args.spec}", file=sys.stderr)
            sys.exit(1)

        solution = "direct" if args.solution in ("direct", "a") else "structured"
        results = asyncio.run(run_from_spec(args.spec, args.output, solution))

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n{'=' * 60}")
            print("RESULTS SUMMARY")
            print(f"{'=' * 60}")
            print(f"Solution: {results['solution']}")
            print(f"Success: {results['success']}")
            print(f"Time: {results['execution_time']:.2f}s")
            if results.get("accuracy"):
                acc = results["accuracy"]
                print(f"Node accuracy: {acc['node_ratio']:.1%}")
                print(f"Edge accuracy: {acc['edge_ratio']:.1%}")
                print(f"Cluster accuracy: {acc['cluster_ratio']:.1%}")
            if results["diagram_path"]:
                print(f"Diagram: {results['diagram_path']}")
            if results["errors"]:
                print(f"Errors: {results['errors']}")

        sys.exit(0 if results["success"] else 1)

    # Interactive mode
    if args.solution in ("direct", "a"):
        asyncio.run(run_direct_interactive())
    else:
        asyncio.run(run_structured_interactive())


def main_direct():
    """Entry point for direct generation."""
    asyncio.run(run_direct_interactive())


def main_structured():
    """Entry point for structured generation."""
    asyncio.run(run_structured_interactive())


if __name__ == "__main__":
    main()
