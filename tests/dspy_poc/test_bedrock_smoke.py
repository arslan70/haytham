"""Smoke test: verify DSPy can talk to Bedrock."""

import os

import dspy


def main():
    model_id = os.environ.get("BEDROCK_HEAVY_MODEL_ID")
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not model_id:
        print("BEDROCK_HEAVY_MODEL_ID not set, skipping smoke test")
        return

    lm = dspy.LM(
        f"bedrock/{model_id}",
        region_name=region,
    )
    dspy.configure(lm=lm)

    qa = dspy.Predict("question -> answer")
    result = qa(question="What is 2+2?")
    print(f"Answer: {result.answer}")
    print("Smoke test PASSED")


if __name__ == "__main__":
    main()
