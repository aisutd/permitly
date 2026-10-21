"""
main.py
=======
STEP 6: The web API (FastAPI). This is what the backend / website calls.

Run it:        uvicorn main:app --reload
Use it here:   http://127.0.0.1:8000        (ONE box: type a description, get the answer)
Dev page:      http://127.0.0.1:8000/docs   (FastAPI makes a free test page)

Endpoints:
  GET  /         -> the one-box web page (see PAGE at the bottom of this file)
  GET  /health   -> is the server alive?
  POST /profile  -> LLM profile only             (works BEFORE training)
  POST /risk     -> risk + 3 similar examples    (needs the trained model)
  POST /assess   -> everything together

Input is ONE text field: {"description": "..."}  (plain text, 10-5000 characters).
Strange input (gibberish, other languages) returns general_risk "Unknown" or a
non-empty "warnings" list with needs_review = true.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from assess import assess_business
from profile_builder import build_profile
from risk_model import predict_risk

app = FastAPI(title="Permitly Risk API")


# The shape of what the user sends us.
class DescriptionIn(BaseModel):
    description: str = Field(min_length=10, max_length=5000)

    @field_validator("description")
    @classmethod
    def must_contain_words(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Description is too short (at least 10 characters).")
        if sum(ch.isalpha() for ch in value) < 5:
            raise ValueError("Description must contain real words, not only numbers or symbols.")
        return value


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return PAGE


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/profile")
def profile(body: DescriptionIn):
    try:
        return build_profile(body.description).model_dump()
    except RuntimeError as error:   # e.g. missing API key
        raise HTTPException(status_code=500, detail=str(error))
    except ValueError as error:     # LLM answer was invalid twice
        raise HTTPException(status_code=502, detail=str(error))


@app.post("/risk")
def risk(body: DescriptionIn):
    try:
        return predict_risk(body.description)
    except FileNotFoundError as error:  # model not trained yet
        raise HTTPException(status_code=503, detail=str(error))


@app.post("/assess")
def assess(body: DescriptionIn):
    try:
        return assess_business(body.description)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error))


# ---------------------------------------------------------------------------
# The web page: ONE box in, the answer out. It calls POST /assess in this server.
# Text from the server is shown with textContent (never as HTML), so it is safe.
# ---------------------------------------------------------------------------
PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Permitly Risk Check</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; background: #f1f5f9; color: #0f172a;
         font: 15px/1.5 -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }
  main { max-width: 760px; margin: 36px auto; padding: 0 16px 60px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .sub { color: #475569; margin: 0 0 16px; }
  textarea { width: 100%; min-height: 150px; padding: 12px; font: inherit; resize: vertical;
             border: 2px solid #94a3b8; border-radius: 10px; background: #fff; color: inherit; }
  textarea:focus { outline: none; border-color: #2563eb; }
  .row { display: flex; align-items: center; gap: 12px; margin-top: 10px; }
  button { background: #2563eb; color: #fff; border: 0; border-radius: 8px; padding: 10px 22px;
           font: inherit; font-weight: 600; cursor: pointer; }
  button:disabled { background: #94a3b8; cursor: wait; }
  #status { color: #475569; }
  .hint { color: #64748b; font-size: 13px; }
  .card { background: #fff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 16px; margin-top: 16px; }
  .badge { display: inline-block; color: #fff; font-weight: 700; font-size: 22px; letter-spacing: 1px;
           padding: 6px 18px; border-radius: 8px; }
  .bar { display: flex; align-items: center; gap: 8px; margin: 6px 0; font-size: 14px; }
  .bar .name { width: 64px; }
  .bar .track { flex: 1; background: #e2e8f0; border-radius: 6px; height: 12px; overflow: hidden; }
  .bar .fill { display: block; height: 100%; }
  .bar .pct { width: 44px; text-align: right; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: #475569; margin: 16px 0 6px; }
  .warn { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 8px 12px; border-radius: 6px; margin-top: 12px; font-size: 14px; }
  .err { background: #fef2f2; border-left: 4px solid #ef4444; padding: 8px 12px; border-radius: 6px; margin-top: 16px; }
  table { border-collapse: collapse; width: 100%; font-size: 14px; }
  td { padding: 5px 8px; border-top: 1px solid #e2e8f0; vertical-align: top; }
  td:first-child { width: 150px; color: #475569; }
  .ex { border-top: 1px solid #e2e8f0; padding: 8px 0; font-size: 14px; }
  .tag { font-weight: 700; margin-right: 6px; }
  details { margin-top: 14px; font-size: 13px; }
  pre { background: #f1f5f9; padding: 10px; border-radius: 8px; overflow: auto; }
</style>
</head>
<body>
<main>
  <h1>Permitly Risk Check</h1>
  <p class="sub">Type or paste a short description of a business (in English). You get a risk level, similar examples, and a profile.</p>
  <textarea id="text" placeholder="Example: We pay gig workers in Mexico and the Philippines every Friday."></textarea>
  <div class="row">
    <button id="go">Analyze</button>
    <span id="status"></span>
    <span class="hint">Tip: Ctrl + Enter also works.</span>
  </div>
  <div id="out"></div>
</main>
<script>
  var COLORS = { High: "#dc2626", Medium: "#d97706", Low: "#16a34a", Unknown: "#64748b" };
  var box = document.getElementById("text");
  var btn = document.getElementById("go");
  var statusEl = document.getElementById("status");
  var out = document.getElementById("out");

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function showError(message) {
    out.innerHTML = "";
    out.appendChild(el("div", "err", message));
  }

  function render(d) {
    out.innerHTML = "";
    var card = el("div", "card");

    var badge = el("span", "badge", d.general_risk.toUpperCase());
    badge.style.background = COLORS[d.general_risk] || COLORS.Unknown;
    card.appendChild(badge);

    var names = ["High", "Medium", "Low"];
    if (d.probabilities && Object.keys(d.probabilities).length) {
      card.appendChild(el("h2", null, "How sure is the model?"));
      names.forEach(function (n) {
        var p = d.probabilities[n] || 0;
        var row = el("div", "bar");
        row.appendChild(el("span", "name", n));
        var track = el("span", "track");
        var fill = el("span", "fill");
        fill.style.width = (p * 100) + "%";
        fill.style.background = COLORS[n];
        track.appendChild(fill);
        row.appendChild(track);
        row.appendChild(el("span", "pct", Math.round(p * 100) + "%"));
        card.appendChild(row);
      });
    }

    (d.warnings || []).forEach(function (w) {
      card.appendChild(el("div", "warn", "Check this result: " + w));
    });

    card.appendChild(el("h2", null, "Profile"));
    if (d.profile) {
      var t = el("table");
      var rows = [["Activities", (d.profile.activities || []).join(", ") || "-"],
                  ["Holds customer funds", d.profile.holds_funds],
                  ["International", d.profile.international],
                  ["Crypto", d.profile.crypto]];
      rows.forEach(function (r) {
        var tr = el("tr");
        tr.appendChild(el("td", null, r[0]));
        tr.appendChild(el("td", null, r[1]));
        t.appendChild(tr);
      });
      card.appendChild(t);
    } else {
      card.appendChild(el("div", "hint", "Not available. " + (d.profile_error || "")));
    }

    if (d.similar_examples && d.similar_examples.length) {
      card.appendChild(el("h2", null, "Most similar labeled examples"));
      d.similar_examples.forEach(function (x) {
        var row = el("div", "ex");
        var tag = el("span", "tag", x.label);
        tag.style.color = COLORS[x.label] || COLORS.Unknown;
        row.appendChild(tag);
        row.appendChild(el("span", "hint", "similarity " + x.similarity.toFixed(2) + " - "));
        row.appendChild(document.createTextNode(x.description));
        card.appendChild(row);
      });
    }

    var det = el("details");
    det.appendChild(el("summary", null, "Show raw JSON"));
    det.appendChild(el("pre", null, JSON.stringify(d, null, 2)));
    card.appendChild(det);
    out.appendChild(card);
  }

  async function run() {
    var text = box.value.trim();
    if (text.length < 10) { showError("Please type at least 10 characters."); return; }
    btn.disabled = true;
    statusEl.textContent = "Analyzing... this can take a few seconds.";
    try {
      var res = await fetch("/assess", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: text })
      });
      var data = await res.json();
      if (!res.ok) {
        var d = data.detail;
        var msg = typeof d === "string" ? d : (d && d[0] && d[0].msg) || "Something went wrong.";
        showError(msg.replace(/^Value error,\s*/, ""));
      } else {
        render(data);
      }
    } catch (e) {
      showError("Cannot reach the server. Is it running?");
    } finally {
      btn.disabled = false;
      statusEl.textContent = "";
    }
  }

  btn.addEventListener("click", run);
  box.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") run();
  });
</script>
</body>
</html>
"""
