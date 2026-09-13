/* Sample OPE audit result — same shape emitted by `ope audit --json`. */
window.OPE_SAMPLE_REPORT = {
  engine: "ope",
  version: "0.1.0",
  run_id: "ope-1726190400",
  target: "https://starbrand.example.com",
  final_url: "https://starbrand.example.com/",
  started_at: 1726190400,
  completed_at: 1726190402.4,
  engine_contract: "evidence-root-cause-v1",
  inventory: {
    status: 200,
    bytes: 48213,
    title: "StarBrand — Digital Presence",
    description: "",
    lang: "en",
    viewport: "",
    canonical: "",
    headings: 11,
    h1: 1,
    links: 47,
    images: 8,
    images_missing_alt: 3,
    forms: 2,
    json_ld_blocks: 0
  },
  modules: Object.assign(
    Object.fromEntries(Array.from({ length: 20 }, (_, i) => {
      const k = String(i + 1).padStart(2, "0");
      return [k, { status: "UNKNOWN", findings: [] }];
    })),
    {
      "03": { status: "FAIL", findings: ["03-CODE-META-001"] },
      "05": { status: "FAIL", findings: ["05-INDEX-CAN-001"] },
      "06": { status: "FAIL", findings: ["06-SEM-JSONLD-001"] },
      "13": { status: "FAIL", findings: ["13-UX-MOBILE-001"] },
      "14": { status: "FAIL", findings: ["14-A11Y-IMG-001"] },
      "16": { status: "FAIL", findings: ["16-SEC-CSP", "16-SEC-HSTS"] },
      "02": { status: "PASS", findings: [] }
    }
  ),
  summary: { finding_count: 7, critical: 0, high: 0, medium: 4, low: 2, info: 1 },
  findings: [
    {
      id: "03-CODE-META-001", module: "03-code", symptom: "Document has no title",
      status: "OBSERVED", severity: "medium", priority: 49.0, confidence: 1.0,
      root_cause: "The application template does not render a <title> element for the route.",
      remediation: ["Add a unique, descriptive title aligned to page intent.", "Wire titles into the shared layout template, not per-page hacks."],
      validation: ["Re-audit title presence and uniqueness across routes."],
      evidence: [{ source: "html-parser", target: "https://starbrand.example.com/", value: { title: "" }, confidence: 1.0 }]
    },
    {
      id: "13-UX-MOBILE-001", module: "13-ux", symptom: "Viewport metadata is missing",
      status: "OBSERVED", severity: "medium", priority: 42.0, confidence: 1.0,
      root_cause: "The shared HTML head partial dropped the viewport declaration during a redesign.",
      remediation: ["Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> to the shared head."],
      validation: ["Validate mobile rendering across representative devices."],
      evidence: [{ source: "html-parser", target: "https://starbrand.example.com/", value: { viewport: "" }, confidence: 1.0 }]
    },
    {
      id: "05-INDEX-CAN-001", module: "05-index", symptom: "No canonical link was detected",
      status: "HYPOTHESIS", severity: "medium", priority: 35.0, confidence: 1.0,
      root_cause: "Not yet established; additional evidence or dependency analysis is required.",
      remediation: ["Define canonicalization deliberately for indexable URLs."],
      validation: ["Confirm canonical points to the intended URL and is crawlable."],
      evidence: [{ source: "html-parser", target: "https://starbrand.example.com/", value: { canonical: "" }, confidence: 1.0 }]
    },
    {
      id: "14-A11Y-IMG-001", module: "14-accessibility", symptom: "3 of 8 images lack useful alt text",
      status: "OBSERVED", severity: "medium", priority: 28.8, confidence: 1.0,
      root_cause: "Marketing images are injected from a CMS field that does not require alt text.",
      remediation: ["Require alt text in the CMS schema for informative images.", "Use empty alt for purely decorative images."],
      validation: ["Re-run accessibility checks and inspect representative images."],
      evidence: [{ source: "html-parser", target: "https://starbrand.example.com/", value: { images: 8, missing_alt: 3 }, confidence: 1.0 }]
    },
    {
      id: "16-SEC-CSP", module: "16-security", symptom: "Recommended security header not observed: content-security-policy",
      status: "OBSERVED", severity: "low", priority: 11.2, confidence: 1.0,
      root_cause: "The edge layer was never configured to emit a Content-Security-Policy header.",
      remediation: ["Review and configure content-security-policy against the application threat model."],
      validation: ["Re-fetch response headers and verify content-security-policy."],
      evidence: [{ source: "http-headers", target: "https://starbrand.example.com/", value: { "content-security-policy": null }, confidence: 1.0 }]
    },
    {
      id: "16-SEC-HSTS", module: "16-security", symptom: "Recommended security header not observed: strict-transport-security",
      status: "OBSERVED", severity: "low", priority: 11.2, confidence: 1.0,
      root_cause: "HSTS was not enabled when TLS was terminated at the CDN.",
      remediation: ["Enable strict-transport-security with an appropriate max-age."],
      validation: ["Re-fetch response headers and verify strict-transport-security."],
      evidence: [{ source: "http-headers", target: "https://starbrand.example.com/", value: { "strict-transport-security": null }, confidence: 1.0 }]
    },
    {
      id: "06-SEM-JSONLD-001", module: "06-semantics", symptom: "No JSON-LD structured data was detected",
      status: "OBSERVED", severity: "info", priority: 3.6, confidence: 1.0,
      root_cause: "Entity schema was planned but never shipped to the template layer.",
      remediation: ["Add schema.org structured data that accurately represents visible content."],
      validation: ["Validate structured data and compare it with visible content."],
      evidence: [{ source: "html-parser", target: "https://starbrand.example.com/", value: { json_ld_blocks: 0 }, confidence: 1.0 }]
    }
  ]
};
