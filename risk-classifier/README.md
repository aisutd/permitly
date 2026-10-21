# Permitly LLM API (Jason)

Reads a business description and returns: risk level (High/Medium/Low), the 3 most
similar labeled examples, and an LLM profile. No database needed.

## Setup (once) - use the VS Code terminal
1. `python3 -m venv venv`
2. Mac: `source venv/bin/activate`   |   Windows: `venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and paste your key (Gemini by default). NEVER commit `.env`.

## Run order
1. `python profile_builder.py`   -> try the LLM profile builder
2. `python train_model.py --data data/labeled_descriptions.csv`   -> train the risk model
   (put the team's CSV in `data/`; only the `description` and `risk` columns are used)
3. `python run_assess.py "We let users send money to family in Vietnam."`   -> full output in the terminal
4. `python test_profile.py`   -> score the profile builder on 10 cases (goal 8/10)
5. `uvicorn main:app --reload`   -> API. Open http://127.0.0.1:8000/docs

Optional: `pip install sentence-transformers` then add `--compare` to train_model.py.