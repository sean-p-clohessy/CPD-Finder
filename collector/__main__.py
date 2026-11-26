from pathlib import Path
import os
from collector.pipeline import collect


def report(result):
    lines = ["## CPD collection health", "", "| Provider/source | Status | Records | Details |", "| --- | --- | ---: | --- |"]
    issues = 0
    for source in result["sources"]:
        problem = source.get("error") or source.get("warning")
        if problem:
            issues += 1
            message = f"{source['provider']} ({source['url']}): {problem}"
            print(message)
            if os.environ.get("GITHUB_ACTIONS"):
                escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                print(f"::error::{escaped}")
        details = problem or str(source.get("coverage", "Collected successfully"))
        details = details.replace("|", "/").replace("\n", " ")
        lines.append(f"| {source['provider']} ({source['url']}) | {source['status']} | {source['count']} | {details} |")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write("\n".join(lines) + "\n")
    return 1 if issues else 0


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = collect(root / "sources.txt", root / "public/data/opportunities.json")
    failures = sum(source["status"] == "error" for source in result["sources"])
    print(f"Collected {len(result['opportunities'])} opportunities; {failures} source(s) need attention")
    raise SystemExit(report(result))
