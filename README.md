# REALITY CHECK AI — Detect What People Miss

**A real-world visual problem detection, safety investigation, and asset management platform powered by Google Gemma 4 multimodal vision.**

Built for the Student Developer Showcase featuring Gemma.

---

## 🌟 The Core Product Principle

> **See the evidence. Understand the uncertainty. Take the next step. Verify the result.**

Most AI image tools jump straight from a photo to an overconfident, unverified conclusion. **Reality Check AI** bridges the gap between raw computer vision and real-world operational response. It rigorously separates:
- **Verified Visual Facts** (details unmistakable in the photograph)
- **Technical Hypotheses** (plausible explanations requiring on-site checks)
- **Optical Boundaries & Uncertainties** (factors that a single camera angle cannot confirm)
- **Explainable Risk Prioritization** (balancing consequence severity against visual confidence)
- **Human-in-the-Loop Sign-Off** (preventing AI hallucinations from closing safety cases without physical verification)

---

## 🏗️ Architecture & Modules

The platform is designed with an enterprise management interface inspired by modern medical and facility management systems (warm white `#F8FAFC`, deep navy `#0F172A`, and restrained teal `#0D9488` accents).

1. **📊 Overview Dashboard**
   - Live KPI cards: Total Inspections, Active In-Flight Cases, Urgent Findings, and Formally Verified Resolutions.
   - Urgency profile charts, real-time activity stream, and cross-case outstanding verification checklists.
   
2. **➕ New Inspection Intake**
   - High-resolution photographic intake (file upload or live camera capture).
   - One-click Judge / Demo scenario presets (*Obstructed Fire Exit*, *Ceiling Water Seepage Above Subpanel*, *Sidewalk Trip Hazard*).
   - Duplicate & recurring location alerts.
   - Real-time Gemma 4 multimodal vision inference pipeline with progress telemetry.

3. **🔬 Visual Evidence Lab**
   - High-definition photograph inspection viewer.
   - Genuine spatial evidence pins and coordinate markers.
   - Side-by-side Evidence vs. Hypothesis vs. Uncertainty matrix.
   - **Before & After Resolution Comparison:** Attach and audit proof of remediation alongside the incident photo.

4. **📋 AI Findings**
   - Comprehensive structured diagnostic breakdown.
   - Explainable risk prioritization with dedicated rationale.
   - Optical confidence rating (kept strictly separate from hazard severity).
   - Context-aware follow-up verification questions.
   - Ready-to-send dispatch message for maintenance and civic ticketing systems.

5. **🛠️ Investigation Workspace**
   - Dynamic, editable verification checklist generated from visual evidence.
   - Assignment management (assignee and target resolution deadlines).
   - Inspector operational field notes log.
   - **Human-in-the-Loop Sign-Off:** Required human authorization and signature statement before a case can transition to Resolved.
   - Complete audit trail and action timeline.

6. **📂 Case Management**
   - Real-time searchable and filterable case registry.
   - Multi-parameter filtering by Status (*Open*, *Investigating*, *Action Required*, *Resolved*, *Reopened*), Priority, and Category.
   - One-click routing into the Evidence Lab and Workspace.

7. **📄 Reports & Export**
   - Browser-printable formal inspection audit reports with embedded evidence photos and sign-off blocks.
   - One-click download as Markdown (`.md`) and plain text (`.txt`).
   - Full case registry CSV export for integration with external spreadsheets or BI dashboards.

8. **📈 Analytics & Trends**
   - Stacked category vs. priority distributions.
   - Donut charts for operational case statuses.
   - Cross-case pattern correlation and recurring problem hotspot detection.

9. **⚙️ Settings & Diagnostics**
   - Live Gemma model connection test tool.
   - Credential security status indicators (protecting API keys from disclosure).
   - Sample data management (reload pre-configured demo cases or clear database).
   - Raw database JSON backup download.

---

## 🚀 Running the Application on Windows

### 1. Open PowerShell in this folder:
```powershell
cd c:\Users\Purvi\Downloads\reality_check_ai
```

### 2. Activate the virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Ensure your Google AI API key is set:
In `.streamlit/secrets.toml`:
```toml
GOOGLE_API_KEY = "your-google-ai-api-key"
```

### 4. Start the application:
```powershell
streamlit run app.py
```

Open the printed URL in your browser: **`http://localhost:8501`**

---

## 🤖 Multimodal Model Specifications

- **Default Model:** `gemma-4-26b-a4b-it` (Google Gemma 4 multimodal instruction-tuned vision model).
- **SDK:** Google Gen AI SDK (`google-genai` >= 1.0.0).
- **Safety Standard:** The system strictly forbids facial recognition, biometric identity inference, or legal liability declarations based solely on visual inference. All findings require physical human verification.
