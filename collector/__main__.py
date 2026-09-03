from pathlib import Path
from collector.pipeline import collect


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = collect(root / "sources.txt", root / "public/data/opportunities.json")
    failures = sum(source["status"] == "error" for source in result["sources"])
    print(f"Collected {len(result['opportunities'])} opportunities; {failures} source(s) need attention")
