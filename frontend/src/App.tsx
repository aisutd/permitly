import {
  FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import usaMap from "@svg-maps/usa";

type RiskLevel = "strict" | "moderate" | "lenient";
type BusinessType = "P2P payments" | "Remittance" | "Crypto" | "Payroll";

type StateProfile = {
  risk: RiskLevel;
  bond: string;
  fees: string;
  note: string;
};

const strictStates = new Set([
  "ca",
  "ct",
  "il",
  "ma",
  "mn",
  "nj",
  "ny",
  "pa",
  "wa",
]);

const lenientStates = new Set(["ak", "mt", "sd", "wy"]);

const profileOverrides: Record<string, Partial<StateProfile>> = {
  ca: {
    bond: "$250,000 minimum",
    fees: "$5,000 application fee",
    note: "Broad licensing scope and substantial supervisory review.",
  },
  ny: {
    bond: "Set by the superintendent",
    fees: "Varies by investigation scope",
    note: "New York applies one of the most intensive review frameworks.",
  },
  pa: {
    bond: "$1,000,000 minimum",
    fees: "$5,000 application fee",
    note: "Higher sample bond threshold and ongoing reporting obligations.",
  },
  tx: {
    bond: "Surety bond: [from statute]",
    fees: "Fees: [from statute]",
    note: "The sample bond may increase based on transmission volume and locations.",
  },
  mt: {
    bond: "No state MTL bond in sample",
    fees: "No state MTL application fee",
    note: "Montana is treated as lenient in this sample classification.",
  },
};

function getProfile(
  stateId: string,
  businessType: BusinessType = "Remittance",
): StateProfile {
  let risk: RiskLevel;

  if (businessType === "Payroll") {
    risk =
      stateId === "mo"
        ? "strict"
        : ["ca", "ny", "tx"].includes(stateId)
          ? "moderate"
          : "lenient";
  } else if (businessType === "Crypto") {
    risk =
      stateId === "ny"
        ? "strict"
        : lenientStates.has(stateId)
          ? "lenient"
          : "moderate";
  } else {
    risk = strictStates.has(stateId)
      ? "strict"
      : lenientStates.has(stateId)
        ? "lenient"
        : "moderate";
  }

  const defaults: Record<RiskLevel, Omit<StateProfile, "risk">> = {
    strict: {
      bond: "State-specific bond required",
      fees: "Higher review and filing fees",
      note: "More extensive licensing, bonding, and examination requirements.",
    },
    moderate: {
      bond: "Volume-based bond may apply",
      fees: "Standard application and renewal fees",
      note: "Licensing is generally required with standard financial safeguards.",
    },
    lenient: {
      bond: "Limited or no state bond in sample",
      fees: "Lower or limited state fees",
      note: "Fewer state-level money transmission requirements in this sample.",
    },
  };

  return { risk, ...defaults[risk], ...profileOverrides[stateId] };
}

const legend = [
  { name: "Strict", className: "strict" },
  { name: "Moderate", className: "moderate" },
  { name: "Lenient", className: "lenient" },
];

const classifierResults = {
  "license-likely": "License likely",
  "likely-exempt": "Likely exempt",
  unclear: "Unclear",
} as const;

const examples = [
  {
    id: "remittance",
    description:
      "We’re building an app that lets gig workers send part of their pay to family abroad.",
    result: "license-likely",
    confidence: "High",
    reason:
      "Your app receives workers’ pay and sends it to family abroad, which most states treat as money transmission.",
    chips: ["holds funds", "pays third parties", "cross-border"],
  },
  {
    id: "marketplace",
    description:
      "A marketplace where buyers pay sellers through our platform. We’re not sure if we hold the funds or our payment partner does.",
    result: "unclear",
    confidence: "Low",
    reason:
      "Depends on who holds the funds and whether you act as the seller’s agent.",
    chips: ["funds holder unknown", "possible agent of payee"],
  },
] as const;

type Assessment = {
  result: keyof typeof classifierResults;
  confidence: string;
  reason: string;
  chips: readonly string[];
  demo: boolean;
};

const suggestedQuestions = [
  {
    id: "texas-bond",
    question: "What’s the bond requirement in Texas?",
    answer:
      "Texas requires the greater of $100,000 or 100% of your average daily money transmission liability, capped at $500,000.",
    citation: "Texas Finance Code Ch. 152",
  },
  {
    id: "montana-license",
    question: "Does Montana require a license?",
    answer:
      "In this sample, Montana does not require a state money transmitter license, but federal requirements may still apply.",
    citation: "Montana Code Annotated",
  },
  {
    id: "payroll-exemption",
    question: "Is payroll processing exempt?",
    answer:
      "Payroll processing may be exempt when the provider acts only as an agent and does not control the underlying funds flow.",
    citation: "State payroll exemption",
  },
] as const;

export default function App() {
  const texas = usaMap.locations.find((state) => state.id === "tx");
  const [selectedExampleId, setSelectedExampleId] = useState("remittance");
  const [description, setDescription] = useState(examples[0].description);
  const [assessment, setAssessment] = useState<Assessment>({
    result: examples[0].result,
    confidence: examples[0].confidence,
    reason: examples[0].reason,
    chips: examples[0].chips,
    demo: false,
  });
  const [isAssessing, setIsAssessing] = useState(false);
  const [selectedId, setSelectedId] = useState("tx");
  const [businessType, setBusinessType] =
    useState<BusinessType>("Remittance");
  const [query, setQuery] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatQuery, setChatQuery] = useState("");
  const [selectedSuggestionId, setSelectedSuggestionId] = useState<
    string | null
  >(null);
  const [citationExpanded, setCitationExpanded] = useState(false);
  const [chatFollowUp, setChatFollowUp] = useState<{
    question: string;
    answer: string;
  } | null>(null);
  const assessmentTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const selectedState = useMemo(
    () =>
      usaMap.locations.find((state) => state.id === selectedId) ??
      texas ??
      usaMap.locations[0],
    [selectedId, texas],
  );
  const selectedProfile = getProfile(selectedState.id, businessType);
  const selectedExample =
    examples.find((example) => example.id === selectedExampleId) ?? examples[0];
  const selectedSuggestion = suggestedQuestions.find(
    (suggestion) => suggestion.id === selectedSuggestionId,
  );

  useEffect(
    () => () => {
      if (assessmentTimer.current) {
        clearTimeout(assessmentTimer.current);
      }
    },
    [],
  );

  function selectExample(example: (typeof examples)[number]) {
    if (assessmentTimer.current) {
      clearTimeout(assessmentTimer.current);
    }
    setIsAssessing(false);
    setSelectedExampleId(example.id);
    setDescription(example.description);
    setAssessment({
      result: example.result,
      confidence: example.confidence,
      reason: example.reason,
      chips: example.chips,
      demo: false,
    });
  }

  function assessDescription() {
    if (assessmentTimer.current) {
      clearTimeout(assessmentTimer.current);
    }
    setIsAssessing(true);

    assessmentTimer.current = setTimeout(() => {
      const normalized = description.toLowerCase();
      const likelyTerms = ["hold", "wallet", "send", "transfer"].filter(
        (term) => normalized.includes(term),
      );
      const exemptTerms = ["software", "never touch", "bank"].filter((term) =>
        normalized.includes(term),
      );

      if (likelyTerms.length > 0) {
        setAssessment({
          result: "license-likely",
          confidence: "High",
          reason:
            "The demo found language suggesting your product may receive or move funds.",
          chips: likelyTerms,
          demo: true,
        });
      } else if (exemptTerms.length > 0) {
        setAssessment({
          result: "likely-exempt",
          confidence: "High",
          reason:
            "The demo found language suggesting software-only services or a bank-controlled funds flow.",
          chips: exemptTerms,
          demo: true,
        });
      } else {
        setAssessment({
          result: "unclear",
          confidence: "Low",
          reason: "The demo did not find a clear funds-flow signal.",
          chips: ["no keyword match"],
          demo: true,
        });
      }

      setIsAssessing(false);
      assessmentTimer.current = null;
    }, 1500);
  }

  function selectState(id: string, name: string) {
    setSelectedId(id);
    setQuery(`What's the bond requirement in ${name}?`);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setChatOpen(true);
  }

  function handleChatSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = chatQuery.trim();
    if (!trimmedQuery) {
      return;
    }

    const matchedState = usaMap.locations.find((state) =>
      chatQuery.toLowerCase().includes(state.name.toLowerCase()),
    );

    if (matchedState) {
      const profile = getProfile(matchedState.id, businessType);
      setSelectedId(matchedState.id);
      setChatFollowUp({
        question: trimmedQuery,
        answer: `${matchedState.name}: ${profile.bond}. ${profile.fees}. ${profile.note}`,
      });
    } else {
      setChatFollowUp({
        question: trimmedQuery,
        answer:
          "Name a U.S. state and ask about its bond requirement, fees, or licensing risk.",
      });
    }
    setChatQuery("");
  }

  return (
    <main className="page-shell">
      <header className="site-header">
        <a className="brand" href="#" aria-label="Permitly home">
          <span className="brand-mark" aria-hidden="true">
            P
          </span>
          <span>Permitly</span>
        </a>
        <nav className="primary-nav" aria-label="Primary navigation">
          <a href="#assess">Assess</a>
          <a href="#state-map">State map</a>
          <a href="#ask">Ask</a>
          <a href="#how-it-works">How it works</a>
        </nav>
        <a className="nav-cta" href="#assess">
          Try a description
        </a>
      </header>

      <div className="workflow-progress" aria-label="Permitly workflow">
        <span>1 Describe</span>
        <span aria-hidden="true">→</span>
        <span className="active" aria-current="step">
          2 Assess
        </span>
        <span aria-hidden="true">→</span>
        <span>3 Explore states</span>
      </div>

      <section className="hero" id="assess" aria-labelledby="page-title">
        <div className="hero-copy">
          <h1 id="page-title">
            <span className="headline-line">Know where your product</span>
            <span className="headline-line headline-accent">
              needs permission.
            </span>
          </h1>
          <p className="hero-description">
            Turn a product description into a clear first look at state money
            transmitter licensing exposure, bonds, and filing fees.
          </p>

          <section className="workflow-stage" aria-labelledby="describe-step">
            <p className="section-step" id="describe-step">
              1 Describe
            </p>
            <div className="example-picker" aria-label="Example descriptions">
              {examples.map((example, index) => (
                <button
                  className={`example-option ${
                    selectedExample.id === example.id ? "active" : ""
                  }`}
                  key={example.id}
                  type="button"
                  aria-pressed={selectedExample.id === example.id}
                  onClick={() => selectExample(example)}
                >
                  <span>Example {index + 1}</span>
                  {example.description}
                </button>
              ))}
            </div>
            <div className="scenario-card">
              <p className="scenario-label">Product description</p>
              <label className="sr-only" htmlFor="product-description">
                Product description
              </label>
              <textarea
                className="scenario-input"
                id="product-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={3}
              />
              <div className="assessment-action">
                <button
                  type="button"
                  onClick={assessDescription}
                  disabled={isAssessing}
                >
                  Assess
                </button>
              </div>
            </div>
          </section>

          <section className="workflow-stage" aria-labelledby="assess-step">
            <p className="section-step active" id="assess-step">
              2 Assess
            </p>
            <div className="scenario-card assessment-card">
              {isAssessing ? (
                <div className="assessment-progress" role="status">
                  <span>Checking state statutes…</span>
                  <div className="progress-track" aria-hidden="true">
                    <span />
                  </div>
                </div>
              ) : (
                <>
                  <div className="risk-row">
                    <span>Classifier result</span>
                    <div className="result-output">
                      <div className="classifier-output">
                        <strong className={`risk-badge ${assessment.result}`}>
                          <span aria-hidden="true" />
                          {classifierResults[assessment.result]}
                        </strong>
                        <span className="confidence">
                          Confidence: {assessment.confidence}
                        </span>
                      </div>
                      {assessment.demo && (
                        <span className="demo-logic">
                          Demo logic, not the real model.
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="result-reason" id="how-it-works">
                    <p className="result-reason-title">Why this result</p>
                    <p>{assessment.reason}</p>
                    <div
                      className="reason-chips"
                      aria-label="Classification signals"
                    >
                      {assessment.chips.map((chip) => (
                        <span key={chip}>{chip}</span>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>

            <form className="prompt-bar" id="ask" onSubmit={handleSubmit}>
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                <path
                  d="m21 21-4.35-4.35m2.35-5.4A7.75 7.75 0 1 1 3.5 11.25a7.75 7.75 0 0 1 15.5 0Z"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              </svg>
              <label className="sr-only" htmlFor="state-prompt">
                Ask Permitly about state requirements
              </label>
              <input
                id="state-prompt"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="What's the bond requirement in Texas?"
              />
              <button type="submit">
                Ask Permitly
                <span aria-hidden="true">↗</span>
              </button>
            </form>
          </section>
        </div>

        <div className="map-panel" id="state-map">
          <p className="section-step">3 Explore states</p>
          <div className="map-heading">
            <div>
              <p className="kicker">State requirements</p>
              <h2>Licensing strictness by state</h2>
            </div>
            <span className="map-count">Sample data</span>
          </div>

          <div className="map-controls">
            <label htmlFor="business-type">Business type</label>
            <select
              id="business-type"
              value={businessType}
              onChange={(event) =>
                setBusinessType(event.target.value as BusinessType)
              }
            >
              <option>P2P payments</option>
              <option>Remittance</option>
              <option>Crypto</option>
              <option>Payroll</option>
            </select>
          </div>

          <div className="map-wrap">
            <svg
              className="usa-map"
              viewBox={usaMap.viewBox}
              role="group"
              aria-label="Interactive map of state money transmission risk"
            >
              {usaMap.locations.map((state) => {
                const profile = getProfile(state.id, businessType);
                return (
                  <path
                    className={`state-shape ${profile.risk} ${
                      selectedId === state.id ? "selected" : ""
                    }`}
                    key={state.id}
                    d={state.path}
                    role="button"
                    tabIndex={0}
                    aria-label={`${state.name}: ${profile.risk} requirements`}
                    onClick={() => selectState(state.id, state.name)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        selectState(state.id, state.name);
                      }
                    }}
                  >
                    <title>
                      {state.name}: {profile.risk}
                    </title>
                  </path>
                );
              })}
            </svg>
          </div>
          <p className="map-note">
            Strictness weights change with business type.
          </p>

          <div className="legend" aria-label="Requirement strictness">
            {legend.map((item) => (
              <div className="legend-item" key={item.name}>
                <span className={`legend-dot ${item.className}`} />
                {item.name}
              </div>
            ))}
          </div>

          <div className="state-detail">
            <div className="state-detail-heading">
              <div>
                <p className="scenario-label">Selected state</p>
                <h3>{selectedState.name}</h3>
              </div>
              <span className={`level-pill ${selectedProfile.risk}`}>
                {selectedProfile.risk}
              </span>
            </div>
            <div className="detail-grid">
              <div>
                <span>Surety bond</span>
                <strong>{selectedProfile.bond}</strong>
              </div>
              <div>
                <span>Fees</span>
                <strong>{selectedProfile.fees}</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer>
        <span>Sample data for product exploration</span>
        <span>Not legal advice · verify with state regulators</span>
      </footer>

      {chatOpen && (
        <>
          <button
            className="chat-backdrop"
            type="button"
            aria-label="Close Permitly chat"
            onClick={() => setChatOpen(false)}
          />
          <aside
            className="chat-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="chat-title"
          >
            <div className="chat-header">
              <div>
                <p className="scenario-label">Compliance assistant</p>
                <h2 id="chat-title">Ask Permitly</h2>
              </div>
              <button
                className="chat-close"
                type="button"
                aria-label="Close chat"
                onClick={() => setChatOpen(false)}
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <path
                    d="M6 6l12 12M18 6 6 18"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </div>

            <div className="chat-suggestions">
              <p>Suggested questions</p>
              <div>
                {suggestedQuestions.map((suggestion) => (
                  <button
                    className={
                      selectedSuggestionId === suggestion.id ? "active" : ""
                    }
                    key={suggestion.id}
                    type="button"
                    onClick={() => {
                      setSelectedSuggestionId(suggestion.id);
                      setCitationExpanded(false);
                    }}
                  >
                    {suggestion.question}
                  </button>
                ))}
              </div>
            </div>

            <div className="chat-thread" aria-live="polite">
              {selectedSuggestion ? (
                <>
                  <div className="chat-message user-message">
                    <span>User</span>
                    <p>{selectedSuggestion.question}</p>
                  </div>
                  <div className="chat-message assistant-message">
                    <div className="assistant-label">
                      <span className="answer-mark" aria-hidden="true">
                        P
                      </span>
                      Permitly
                    </div>
                    <p>{selectedSuggestion.answer}</p>
                    <button
                      className="citation-chip"
                      type="button"
                      aria-expanded={citationExpanded}
                      onClick={() => setCitationExpanded((expanded) => !expanded)}
                    >
                      {selectedSuggestion.citation}
                    </button>
                    {citationExpanded && (
                      <div className="citation-excerpt">
                        Statute excerpt: [placeholder]
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="chat-empty">
                  Select a suggested question or ask about any state’s rules.
                </div>
              )}

              {chatFollowUp && (
                <>
                  <div className="chat-message user-message">
                    <span>User</span>
                    <p>{chatFollowUp.question}</p>
                  </div>
                  <div className="chat-message assistant-message">
                    <div className="assistant-label">
                      <span className="answer-mark" aria-hidden="true">
                        P
                      </span>
                      Permitly
                    </div>
                    <p>{chatFollowUp.answer}</p>
                  </div>
                </>
              )}
            </div>

            <form className="chat-input" onSubmit={handleChatSubmit}>
              <label className="sr-only" htmlFor="chat-question">
                Ask about any state’s rules
              </label>
              <input
                id="chat-question"
                value={chatQuery}
                onChange={(event) => setChatQuery(event.target.value)}
                placeholder="Ask about any state’s rules…"
                autoFocus
              />
              <button type="submit" aria-label="Send question">
                ↗
              </button>
            </form>
          </aside>
        </>
      )}
    </main>
  );
}
