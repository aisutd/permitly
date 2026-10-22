"""
run_assess.py
=============
Try the whole pipeline from the terminal, no web server needed.

  python run_assess.py "We let users send money to family in Vietnam."
  python run_assess.py            (it will ask you to type a description)

It prints the risk level + the 3 most similar labeled examples (from the trained
model) and the LLM profile (needs LLM_API_KEY in .env). If the key is missing,
it still prints the risk part.
"""

import json
import sys

from assess import assess_business
from risk_model import predict_risk


def main() -> None:
    text = " ".join(sys.argv[1:]).strip() or input("Business description: ").strip()
    try:
        result = assess_business(text)
    except RuntimeError as error:  # e.g. LLM key missing
        print(f"(Profile skipped: {error})\n")
        result = predict_risk(text)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
