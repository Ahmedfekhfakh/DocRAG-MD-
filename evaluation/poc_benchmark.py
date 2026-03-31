"""150-question MedMCQA POC benchmark."""
import asyncio
import argparse
from agents.eval_agent import run_evaluation


async def main(n: int, models: list[str]):
    report = await run_evaluation(n_questions=n, models=models)
    print(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=150)
    parser.add_argument("--models", nargs="+", default=["gemini"])
    args = parser.parse_args()
    asyncio.run(main(args.n, args.models))
