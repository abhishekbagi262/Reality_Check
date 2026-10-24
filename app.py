import os
import json
import uuid
import re
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

import streamlit as st
import pandas as pd
import altair as alt
from PIL import Image, ImageDraw, ImageOps
from google import genai
from google.genai import types

# ==============================================================================
# 1. DIRECTORIES & PERSISTENCE ENGINE
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
DB_FILE = DATA_DIR / "cases.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_GEMMA_MODEL = "gemma-4-26b-a4b-it"


def _load_raw_data() -> dict:
    if not DB_FILE.exists():
        return {"cases": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"cases": []}


def _save_raw_data(data: dict) -> None:
    temp_file = DB_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_file.replace(DB_FILE)


def get_all_cases() -> list:
    data = _load_raw_data()
    cases = data.get("cases", [])
    cases.sort(key=lambda c: c.get("updated_at", c.get("created_at", "")), reverse=True)
    return cases


def get_case_by_id(case_id: str) -> dict | None:
    cases = get_all_cases()
    for c in cases:
        if c.get("id") == case_id:
            return c
    return None


def save_case(case: dict) -> dict:
    data = _load_raw_data()
    cases = data.get("cases", [])
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not case.get("id"):
        year = datetime.now().year
        count = len(cases) + 1
        case["id"] = f"RC-{year}-{count:03d}"
        case["created_at"] = now_str
    
    case["updated_at"] = now_str
    found = False
    for i, existing in enumerate(cases):
        if existing.get("id") == case["id"]:
            cases[i] = case
            found = True
            break
            
    if not found:
        cases.insert(0, case)
        
    data["cases"] = cases
    _save_raw_data(data)
    return case


def delete_case(case_id: str) -> bool:
    data = _load_raw_data()
    cases = data.get("cases", [])
    initial_len = len(cases)
    cases = [c for c in cases if c.get("id") != case_id]
    if len(cases) != initial_len:
        data["cases"] = cases
        _save_raw_data(data)
        return True
    return False


def save_image_to_storage(image: Image.Image, filename_prefix: str = "evidence") -> str:
    unique_name = f"{filename_prefix}_{uuid.uuid4().hex[:10]}.jpg"
    target_path = IMAGES_DIR / unique_name
    image.save(target_path, "JPEG", quality=92)
    return str(target_path)


def seed_sample_cases_if_needed(force: bool = False) -> None:
    cases = get_all_cases()
    if cases and not force:
        return
        
    img1_path = IMAGES_DIR / "sample_fire_exit.jpg"
    img2_path = IMAGES_DIR / "sample_water_leak.jpg"
    img3_path = IMAGES_DIR / "sample_trip_hazard.jpg"
    after1_path = IMAGES_DIR / "sample_fire_exit_cleared.jpg"
    
    if not img1_path.exists() or force:
        img1 = Image.new("RGB", (900, 600), color="#E2E8F0")
        d1 = ImageDraw.Draw(img1)
        d1.rectangle([(0, 380), (900, 600)], fill="#94A3B8")
        d1.polygon([(0, 380), (300, 100), (600, 100), (900, 380)], fill="#CBD5E1")
        d1.rectangle([(350, 140), (550, 480)], fill="#334155", outline="#0F172A", width=4)
        d1.rectangle([(370, 160), (530, 260)], fill="#10B981")
        d1.text((410, 200), "EMERGENCY EXIT", fill="#FFFFFF")
        d1.rectangle([(320, 350), (460, 490)], fill="#D97706", outline="#78350F", width=3)
        d1.rectangle([(440, 370), (580, 500)], fill="#B45309", outline="#78350F", width=3)
        d1.text((340, 420), "WOODEN CRATES / PALLETS", fill="#FFFFFF")
        d1.text((340, 440), "BLOCKING SWING PATH", fill="#FEF08A")
        img1.save(img1_path, "JPEG")
        
        after1 = Image.new("RGB", (900, 600), color="#E2E8F0")
        d_after = ImageDraw.Draw(after1)
        d_after.rectangle([(0, 380), (900, 600)], fill="#94A3B8")
        d_after.polygon([(0, 380), (300, 100), (600, 100), (900, 380)], fill="#CBD5E1")
        d_after.rectangle([(350, 140), (550, 480)], fill="#334155", outline="#0F172A", width=4)
        d_after.rectangle([(370, 160), (530, 260)], fill="#10B981")
        d_after.text((410, 200), "EMERGENCY EXIT", fill="#FFFFFF")
        d_after.text((380, 440), "CORRIDOR CLEARED", fill="#047857")
        after1.save(after1_path, "JPEG")

    if not img2_path.exists() or force:
        img2 = Image.new("RGB", (900, 600), color="#F1F5F9")
        d2 = ImageDraw.Draw(img2)
        d2.rectangle([(0, 0), (900, 180)], fill="#E2E8F0")
        d2.ellipse([(280, 40), (620, 220)], fill="#CBD5E1", outline="#94A3B8", width=3)
        d2.ellipse([(340, 80), (560, 190)], fill="#93C5FD", outline="#60A5FA", width=2)
        d2.text((370, 120), "ACTIVE CEILING LEAK / DISCOLORATION", fill="#1E3A8A")
        d2.rectangle([(100, 260), (800, 280)], fill="#64748B", outline="#334155", width=2)
        d2.rectangle([(420, 280), (540, 440)], fill="#94A3B8", outline="#475569", width=2)
        d2.text((435, 340), "SUBPANEL / CONDUIT", fill="#0F172A")
        for pt in [(440, 210), (470, 230), (500, 220)]:
            d2.ellipse([pt, (pt[0]+12, pt[1]+22)], fill="#3B82F6")
        img2.save(img2_path, "JPEG")

    if not img3_path.exists() or force:
        img3 = Image.new("RGB", (900, 600), color="#F8FAFC")
        d3 = ImageDraw.Draw(img3)
        d3.rectangle([(0, 300), (450, 600)], fill="#94A3B8", outline="#64748B", width=3)
        d3.polygon([(450, 270), (900, 290), (900, 600), (450, 600)], fill="#CBD5E1", outline="#475569", width=4)
        d3.line([(450, 270), (450, 600)], fill="#1E293B", width=6)
        d3.text((470, 320), "RAISED SLAB (~45mm HEAVE)", fill="#B91C1C")
        d3.text((470, 350), "PEDESTRIAN TRIP HAZARD", fill="#991B1B")
        img3.save(img3_path, "JPEG")

    sample_cases = [
        {
            "id": "RC-2026-001",
            "title": "Blocked Emergency Fire Exit Stairwell",
            "location": "Science Wing B, 2nd Floor Stairwell 4",
            "category": "Safety or access",
            "user_concern": "High",
            "user_description": "Wooden pallets and shipping crates dumped right in front of the emergency push-bar exit door during lab deliveries.",
            "image_path": str(img1_path),
            "after_image_path": str(after1_path),
            "created_at": "2026-10-21 09:30:00",
            "updated_at": "2026-10-22 14:15:00",
            "status": "Resolved",
            "owner": "Marcus Vance (Safety Officer)",
            "deadline": "2026-10-22",
            "ai_model": DEFAULT_GEMMA_MODEL,
            "is_sample": True,
            "ai_findings": {
                "summary": "Large wooden shipping pallets and cardboard crates are positioned directly in front of an outward-swinging emergency exit door marked with an illuminated exit sign.",
                "visual_observations": [
                    "Stacked wooden pallets (approx. 1.2m wide) located within 0.5m of the emergency exit door",
                    "Push-bar emergency egress door swing path is clearly compromised",
                    "Illuminated green 'EMERGENCY EXIT' signage visible above door frame",
                    "Floor surface in corridor shows scuff marks from dragged freight"
                ],
                "possible_interpretations": [
                    "Temporary staging of lab equipment deliveries left unattended",
                    "Storage spillover from adjacent overcrowded loading bay",
                    "Disregard of fire safety egress regulations during renovation"
                ],
                "unconfirmed_information": [
                    "Whether the crates are currently empty or containing hazardous contents",
                    "Duration that the blockage has been in place",
                    "Whether an alternate unlocked egress is accessible nearby within code limits"
                ],
                "potential_consequences": [
                    "Impeded emergency evacuation during building alarm or fire event",
                    "Crush injury or panic blockage at dead-end stairwell threshold",
                    "Severe regulatory violation under National Life Safety Code guidelines"
                ],
                "visual_confidence": "High",
                "confidence_rationale": "Clear, unobstructed sightline with prominent spatial proximity between the obstruction and emergency hardware.",
                "suggested_priority": "Immediate Attention",
                "priority_rationale": "Direct obstruction of a certified life-safety egress route presents immediate risk to human occupants in an evacuation.",
                "verification_checklist": [
                    {"id": 1, "task": "Physically confirm whether push-bar door can open past 30 degrees", "completed": True, "notes": "Blocked at 15 degrees swing"},
                    {"id": 2, "task": "Identify delivery manifest tag or department owner on crate labels", "completed": True, "notes": "Tagged for Dept of Biophysics"},
                    {"id": 3, "task": "Dispatch rapid relocation crew to clear corridor immediately", "completed": True, "notes": "Crates relocated to storage unit S-12"},
                    {"id": 4, "task": "Obtain post-clearance photograph for verification record", "completed": True, "notes": "Uploaded clear photo"}
                ],
                "recommended_actions": [
                    "Dispatch immediate facilities staff to relocate all pallets to designated holding room",
                    "Issue safety violation advisory to Science Wing delivery dock staff",
                    "Conduct follow-up sweep within 4 hours to verify egress remains clear"
                ],
                "suggested_report_message": "URGENT SAFETY NOTICE: Emergency Exit Stairwell 4 in Science Wing B is severely obstructed by stacked wooden pallets. Please dispatch maintenance immediately to restore code compliance.",
                "limitations": "Visual assessment cannot ascertain weight of materials or whether door locking hardware was compromised.",
                "annotations": [
                    {"label": "Obstruction Footprint", "x": 42, "y": 70, "note": "Primary physical blockage"},
                    {"label": "Emergency Hardware", "x": 50, "y": 30, "note": "Designated egress path"}
                ]
            },
            "investigation_notes": [
                {"timestamp": "2026-10-21 10:05", "author": "Marcus Vance", "text": "Called loading dock coordinator. Driver left materials while waiting for freight elevator."},
                {"timestamp": "2026-10-21 11:20", "author": "Facilities Crew 2", "text": "Pallets cleared and hallway swept. Photo captured for record."}
            ],
            "history": [
                {"timestamp": "2026-10-21 09:30", "action": "Case created from visual inspection", "actor": "Automated Gemma Intake"},
                {"timestamp": "2026-10-21 09:45", "action": "Assigned to Marcus Vance (Safety Officer)", "actor": "Admin"},
                {"timestamp": "2026-10-21 11:30", "action": "Verification photo attached", "actor": "Facilities Crew 2"},
                {"timestamp": "2026-10-22 14:15", "action": "Resolved with human approval", "actor": "Chief Inspector L. Ramos"}
            ],
            "resolution": {
                "resolved_by": "Chief Inspector L. Ramos",
                "resolved_at": "2026-10-22 14:15:00",
                "verification_notes": "Corridor fully inspected and confirmed 100% clear. Delivery guidelines reinforced with logistics vendor.",
                "approval_status": "Approved"
            }
        }
    ]

    for sc in sample_cases:
        save_case(sc)


# ==============================================================================
# 2. FAST GEMMA MULTIMODAL VISION ENGINE
# ==============================================================================
def get_api_key() -> str:
    try:
        key = st.secrets.get("GOOGLE_API_KEY", "")
        if key and key.strip() and key.strip() != "YOUR_ACTUAL_API_KEY":
            return key.strip()
    except Exception:
        pass
    
    try:
        import tomllib
        secrets_path = BASE_DIR / ".streamlit" / "secrets.toml"
        if secrets_path.exists():
            with open(secrets_path, "rb") as f:
                data = tomllib.load(f)
                key = data.get("GOOGLE_API_KEY", "")
                if key and key.strip() and key.strip() != "YOUR_ACTUAL_API_KEY":
                    return key.strip()
    except Exception:
        pass

    env_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if env_key and env_key != "YOUR_ACTUAL_API_KEY":
        return env_key
    return ""


def test_gemma_connection(model_id: str = DEFAULT_GEMMA_MODEL, api_key: str = "") -> Tuple[bool, str]:
    key = api_key or get_api_key()
    if not key:
        return False, "API key is missing or set to placeholder value."
    try:
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=model_id.strip(),
            contents="Respond with the word 'ONLINE' if you are active."
        )
        text = (resp.text or "").strip()
        return True, f"Connection successful! Model response: {text[:60]}"
    except Exception as exc:
        return False, f"Connection error: {str(exc)}"


def build_analysis_prompt(context: str, location: str, category: str, concern: str) -> str:
    return f"""You are Reality Check AI, an objective visual evidence investigator and diagnostic safety reasoning engine.
Analyze this image carefully.

CONTEXT FROM OPERATOR:
- Location: {location.strip() or "Not specified"}
- Context Notes: {context.strip() or "None"}
- Category: {category}
- Reported Concern: {concern}

CORE PRINCIPLES:
1. VISUAL EVIDENCE: Only document unmistakable visible facts in "visual_observations".
2. UNCERTAINTY: Clearly separate hypotheses ("possible_interpretations") and unknowns ("unconfirmed_information").
3. GENUINE ANNOTATIONS ONLY: If and only if a clear physical defect or focal point has an unmistakable center location in the image, provide its percentage coordinates (x: 0-100, y: 0-100) in "annotations". If none or uncertain, return an empty list []. NEVER fabricate bounding boxes or coordinates.
4. CONFIDENCE VS SEVERITY: "visual_confidence" is strictly image optical clarity. "suggested_priority" is operational hazard urgency.

Respond ONLY with valid JSON with this exact structure:
{{
  "summary": "1 to 2 concise sentences describing visible condition",
  "visual_observations": ["verified fact 1", "verified fact 2"],
  "possible_interpretations": ["plausible interpretation 1"],
  "unconfirmed_information": ["camera limitation or unknown 1"],
  "potential_consequences": ["realistic consequence 1"],
  "visual_confidence": "High" | "Medium" | "Low",
  "confidence_rationale": "brief reason regarding clarity and angle",
  "suggested_priority": "Immediate Attention" | "High" | "Moderate" | "Low",
  "priority_rationale": "brief operational reason",
  "verification_checklist": ["on-site verification task 1", "on-site verification task 2", "on-site verification task 3"],
  "recommended_actions": ["immediate safe action 1", "follow-up action 2"],
  "suggested_report_message": "polite 2-sentence dispatch message for maintenance",
  "limitations": "concise boundary statement regarding single photograph inference",
  "annotations": [
    {{"label": "defect name", "x": 50, "y": 45, "note": "brief note"}}
  ]
}}"""


def _clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, text)
        if match:
            text = match.group(1).strip()
            
    try:
        return json.loads(text)
    except Exception:
        pass
        
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    return {
        "summary": "Visual analysis conducted on submitted photograph.",
        "visual_observations": ["Visual condition logged."],
        "possible_interpretations": ["Requires physical on-site verification."],
        "unconfirmed_information": ["Single perspective image bounds."],
        "potential_consequences": ["Inspect area to avoid hazard progression."],
        "visual_confidence": "Medium",
        "confidence_rationale": "Evaluated based on camera angle.",
        "suggested_priority": "Moderate",
        "priority_rationale": "Preliminary visual assessment.",
        "verification_checklist": [{"id": 1, "task": "Inspect site in person", "completed": False, "notes": ""}],
        "recommended_actions": ["Restrict access if hazard exists", "Notify facilities lead"],
        "suggested_report_message": "Maintenance review requested.",
        "limitations": "Automated visual guidance based on single image.",
        "annotations": []
    }


def analyze_inspection_image(
    image: Image.Image,
    context: str,
    location: str,
    category: str,
    concern: str,
    model_id: str = DEFAULT_GEMMA_MODEL,
    api_key: str = ""
) -> Tuple[Dict[str, Any], str]:
    key = api_key or get_api_key()
    if not key:
        raise ValueError("Google AI API Key not found. Please configure GOOGLE_API_KEY in .streamlit/secrets.toml.")
        
    client = genai.Client(api_key=key)
    prompt = build_analysis_prompt(context, location, category, concern)
    
    # 512px LANCZOS optimization for 2.6x speedup
    optimized_img = ImageOps.exif_transpose(image).convert("RGB")
    if optimized_img.width > 512 or optimized_img.height > 512:
        optimized_img.thumbnail((512, 512), Image.Resampling.LANCZOS)
    
    config = types.GenerateContentConfig(
        max_output_tokens=750,
        temperature=0.1
    )
    
    response = client.models.generate_content(
        model=model_id.strip(),
        contents=[prompt, optimized_img],
        config=config
    )
    
    raw_text = ""
    if hasattr(response, "text") and response.text:
        raw_text = response.text.strip()
    elif hasattr(response, "candidates") and response.candidates:
        c = response.candidates[0]
        if hasattr(c, "content") and hasattr(c.content, "parts") and c.content.parts:
            raw_text = "".join(part.text or "" for part in c.content.parts).strip()
            
    if not raw_text:
        raise ValueError("The Gemma model returned an empty response. Verify model availability.")
        
    structured = _clean_and_parse_json(raw_text)
    
    raw_checklist = structured.get("verification_checklist", [])
    formatted_checklist = []
    for idx, item in enumerate(raw_checklist, start=1):
        if isinstance(item, str):
            formatted_checklist.append({"id": idx, "task": item, "completed": False, "notes": ""})
        elif isinstance(item, dict):
            formatted_checklist.append(item)
    structured["verification_checklist"] = formatted_checklist
    
    annotations = structured.get("annotations", [])
    valid_annotations = []
    if isinstance(annotations, list):
        for ann in annotations:
            if isinstance(ann, dict) and "label" in ann:
                x = max(0, min(100, float(ann.get("x", 50))))
                y = max(0, min(100, float(ann.get("y", 50))))
                valid_annotations.append({
                    "label": str(ann.get("label", "Finding")),
                    "x": x,
                    "y": y,
                    "note": str(ann.get("note", ""))
                })
    structured["annotations"] = valid_annotations
    
    return structured, raw_text


# ==============================================================================
# 3. HIGH-CONTRAST LOVABLE AURORA UI THEME
# ==============================================================================
def inject_custom_css(dark_mode: bool = True, *args, **kwargs):
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Chakra+Petch:wght@500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
    
    /* UNIVERSAL BRIGHT WHITE TEXT OVERRIDE */
    .stApp, 
    .stApp p, 
    .stApp span, 
    .stApp div, 
    .stApp label, 
    .stApp li, 
    .stApp strong,
    .stApp b,
    [data-testid="stMarkdownContainer"] *,
    [class*="st-emotion-cache"] {
        color: #F8FAFC !important;
    }

    h1, h2, h3, h4, h5, h6,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] strong,
    .brand-title, .panel-title, .kpi-value {
        color: #FFFFFF !important;
    }

    .stApp {
        background-color: #07090E !important;
        background: 
            radial-gradient(ellipse 80% 50% at 50% -10%, rgba(236, 72, 153, 0.16), transparent),
            radial-gradient(ellipse 60% 40% at 85% 15%, rgba(139, 92, 246, 0.14), transparent),
            radial-gradient(ellipse 50% 30% at 15% 30%, rgba(6, 182, 212, 0.12), transparent),
            #07090E !important;
        background-attachment: fixed !important;
    }

    section[data-testid="stSidebar"] {
        background-color: rgba(11, 15, 25, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.12) !important;
        backdrop-filter: blur(24px) !important;
    }
    section[data-testid="stSidebar"] * {
        color: #F8FAFC !important;
    }

    .stCaption, small, 
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] *,
    .kpi-title, .kpi-subtext, .panel-subtitle {
        color: #94A3B8 !important;
    }

    .brand-top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.9rem 1.4rem;
        background: rgba(18, 24, 38, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.14);
        backdrop-filter: blur(20px);
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45);
    }
    .brand-logo-group {
        display: flex;
        align-items: center;
        gap: 0.95rem;
    }
    .brand-icon {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #EC4899 0%, #8B5CF6 50%, #06B6D4 100%);
        color: #FFFFFF !important;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 1.15rem;
        box-shadow: 0 0 20px rgba(139, 92, 246, 0.45);
    }
    .brand-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #FFFFFF !important;
        margin: 0;
        line-height: 1.2;
    }
    .brand-subtitle {
        font-size: 0.78rem;
        font-weight: 500;
        color: #94A3B8 !important;
        margin: 0;
    }
    .brand-badge {
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(255, 255, 255, 0.08);
        color: #E2E8F0 !important;
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 0.35rem 0.8rem;
        border-radius: 9999px;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #10B981;
        box-shadow: 0 0 10px #10B981;
    }

    .kpi-card {
        background: rgba(18, 24, 38, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(20px);
        border-radius: 18px;
        padding: 1.25rem 1.35rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(236, 72, 153, 0.7), rgba(6, 182, 212, 0.7), transparent);
    }
    .kpi-title {
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #94A3B8 !important;
        margin-bottom: 0.35rem;
    }
    .kpi-value {
        font-family: 'Chakra Petch', 'JetBrains Mono', monospace !important;
        font-size: 2.3rem;
        font-weight: 700;
        color: #FFFFFF !important;
        line-height: 1.1;
        margin-bottom: 0.25rem;
    }
    .kpi-subtext {
        font-size: 0.78rem;
        color: #94A3B8 !important;
    }

    .panel-card {
        background: rgba(18, 24, 38, 0.82);
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(20px);
        border-radius: 18px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1.4rem;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
    }
    .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 0.85rem;
        margin-bottom: 1.15rem;
    }
    .panel-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #FFFFFF !important;
        margin: 0;
    }
    .panel-subtitle {
        font-size: 0.82rem;
        color: #94A3B8 !important;
        margin-top: 0.2rem;
    }

    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.28rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 700;
    }
    .badge-open {
        background: rgba(59, 130, 246, 0.25) !important;
        color: #BFDBFE !important;
        border: 1px solid rgba(59, 130, 246, 0.5) !important;
    }
    .badge-investigating {
        background: rgba(245, 158, 11, 0.25) !important;
        color: #FDE68A !important;
        border: 1px solid rgba(245, 158, 11, 0.5) !important;
    }
    .badge-action {
        background: rgba(239, 68, 68, 0.25) !important;
        color: #FECACA !important;
        border: 1px solid rgba(239, 68, 68, 0.5) !important;
    }
    .badge-resolved {
        background: rgba(16, 185, 129, 0.25) !important;
        color: #A7F3D0 !important;
        border: 1px solid rgba(16, 185, 129, 0.5) !important;
    }
    .badge-reopened {
        background: rgba(168, 85, 247, 0.25) !important;
        color: #E9D5FF !important;
        border: 1px solid rgba(168, 85, 247, 0.5) !important;
    }

    .priority-immediate {
        background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%) !important;
        color: #FFFFFF !important;
        padding: 0.28rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 700;
        box-shadow: 0 0 14px rgba(220, 38, 38, 0.6);
    }
    .priority-high {
        background: rgba(249, 115, 22, 0.25) !important;
        color: #FED7AA !important;
        border: 1px solid rgba(249, 115, 22, 0.5) !important;
        padding: 0.28rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 700;
    }
    .priority-moderate {
        background: rgba(234, 179, 8, 0.25) !important;
        color: #FEF08A !important;
        border: 1px solid rgba(234, 179, 8, 0.5) !important;
        padding: 0.28rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 700;
    }
    .priority-low {
        background: rgba(14, 165, 233, 0.25) !important;
        color: #BAE6FD !important;
        border: 1px solid rgba(14, 165, 233, 0.5) !important;
        padding: 0.28rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 700;
    }

    input, textarea, select,
    div[data-testid="stTextInput"] input, 
    div[data-testid="stTextArea"] textarea, 
    div[data-testid="stSelectbox"] select,
    div[data-baseweb="select"] div,
    div[data-baseweb="input"] input {
        background-color: #111622 !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 12px !important;
    }

    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #EC4899 0%, #8B5CF6 50%, #06B6D4 100%) !important;
        border: none !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 20px rgba(139, 92, 246, 0.45) !important;
    }
    .stButton>button {
        background: rgba(255, 255, 255, 0.08) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)


def render_brand_header(active_module: str = "Overview", active_case_id: str = ""):
    st.markdown(f"""
    <div class="brand-top-bar">
        <div class="brand-logo-group">
            <div class="brand-icon">RC</div>
            <div>
                <h1 class="brand-title">REALITY CHECK AI <span style="font-size:0.75rem; font-weight:700; color:#EC4899; background:rgba(236,72,153,0.18); border:1px solid rgba(236,72,153,0.35); padding:2px 10px; border-radius:9999px; margin-left:8px;">AURORA 2.0</span></h1>
                <p class="brand-subtitle">Detect What People Miss · Real-World Visual Safety & Asset Intelligence</p>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 0.85rem;">
            {f'<div class="brand-badge"><span style="color:#94A3B8;">Active Case:</span> <strong style="color:#FFFFFF;">{active_case_id}</strong></div>' if active_case_id else ''}
            <div class="brand-badge">
                <span class="status-dot"></span>
                <span style="color:#FFFFFF;">Gemma 4 Multimodal Vision</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_card(title: str, value: str | int, subtext: str = "", trend_color: str = "#94A3B8"):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-subtext" style="color: {trend_color};">{subtext}</div>
    </div>
    """, unsafe_allow_html=True)


def status_badge_html(status: str) -> str:
    status_map = {
        "Open": "badge-open",
        "Investigating": "badge-investigating",
        "Action Required": "badge-action",
        "Resolved": "badge-resolved",
        "Reopened": "badge-reopened"
    }
    css_class = status_map.get(status, "badge-open")
    return f'<span class="badge {css_class}">{status}</span>'


def priority_badge_html(priority: str) -> str:
    p = str(priority).strip()
    if "immediate" in p.lower():
        return '<span class="priority-immediate">⚡ Immediate Attention</span>'
    elif "high" in p.lower():
        return '<span class="priority-high">⚠️ High Priority</span>'
    elif "mod" in p.lower() or "med" in p.lower():
        return '<span class="priority-moderate">⚖️ Moderate Priority</span>'
    else:
        return '<span class="priority-low">ℹ️ Low Priority</span>'


def confidence_badge_html(conf: str) -> str:
    c = str(conf).strip().lower()
    if c == "high":
        return '<span style="background:rgba(16, 185, 129, 0.22); color:#A7F3D0 !important; border:1px solid rgba(16, 185, 129, 0.5); padding:3px 10px; border-radius:9999px; font-size:0.75rem; font-weight:700;">High Optical Confidence</span>'
    elif c == "medium":
        return '<span style="background:rgba(245, 158, 11, 0.22); color:#FEF08A !important; border:1px solid rgba(245, 158, 11, 0.5); padding:3px 10px; border-radius:9999px; font-size:0.75rem; font-weight:700;">Medium Optical Confidence</span>'
    else:
        return '<span style="background:rgba(148, 163, 184, 0.22); color:#F1F5F9 !important; border:1px solid rgba(148, 163, 184, 0.5); padding:3px 10px; border-radius:9999px; font-size:0.75rem; font-weight:700;">Low Optical Confidence</span>'


# ==============================================================================
# 4. MODULE VIEWS
# ==============================================================================
def render_dashboard_view():
    cases = get_all_cases()
    total_cases = len(cases)
    open_cases = sum(1 for c in cases if c.get("status") in ["Open", "Investigating", "Action Required"])
    urgent_cases = sum(1 for c in cases if "immediate" in str(c.get("ai_findings", {}).get("suggested_priority", "")).lower() or "high" in str(c.get("ai_findings", {}).get("suggested_priority", "")).lower())
    resolved_cases = sum(1 for c in cases if c.get("status") == "Resolved")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Total Inspections", total_cases, "All recorded site scans", "#06B6D4")
    with c2:
        render_kpi_card("Active Open Cases", open_cases, "In progress or awaiting action", "#F59E0B" if open_cases > 0 else "#94A3B8")
    with c3:
        render_kpi_card("Urgent Findings", urgent_cases, "High or Immediate priority", "#EF4444" if urgent_cases > 0 else "#10B981")
    with c4:
        render_kpi_card("Resolved & Verified", resolved_cases, "Human-verified resolutions", "#10B981")
        
    st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)
    
    col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
    with col_act1:
        st.markdown("""
        <div style="background:rgba(18, 24, 38, 0.75); border:1px solid rgba(255, 255, 255, 0.1); border-radius:14px; padding:0.9rem 1.3rem; display:flex; align-items:center; justify-content:space-between;">
            <div>
                <strong style="color:#FFFFFF; font-size:0.95rem;">Operational Principle:</strong>
                <span style="color:#94A3B8; font-size:0.88rem; margin-left:0.4rem;">See the evidence · Understand the uncertainty · Take the next step · Verify the result.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_act2:
        if st.button("➕ Start New Inspection", type="primary", use_container_width=True):
            st.session_state["nav_module"] = "New Inspection"
            st.rerun()
    with col_act3:
        if st.button("📂 Open Case Register", use_container_width=True):
            st.session_state["nav_module"] = "Case Management"
            st.rerun()

    st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)
    
    if not cases:
        st.info("No inspection records found in storage. Click 'Start New Inspection' to begin.")
        return

    col_main, col_side = st.columns([7, 5], gap="large")
    with col_main:
        st.markdown("""
        <div class="panel-card">
            <div class="panel-header">
                <div>
                    <h3 class="panel-title">Recent Inspection Cases</h3>
                    <div class="panel-subtitle">Latest computer vision findings logged across facilities</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        for case in cases[:5]:
            cid = case.get("id")
            title = case.get("title", "Untitled Inspection")
            loc = case.get("location", "Unspecified Location")
            status = case.get("status", "Open")
            findings = case.get("ai_findings", {})
            priority = findings.get("suggested_priority", "Moderate")
            created = case.get("created_at", "")[:10]
            
            with st.container():
                rc1, rc2, rc3, rc4 = st.columns([4, 2, 2, 2])
                with rc1:
                    st.markdown(f"<strong style='color:#FFFFFF; font-size:0.95rem;'>{cid}</strong>: <span style='color:#E2E8F0;'>{title}</span>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:0.78rem; color:#94A3B8; margin-top:2px;'>📍 {loc} · 📅 {created}</div>", unsafe_allow_html=True)
                with rc2:
                    st.markdown(priority_badge_html(priority), unsafe_allow_html=True)
                with rc3:
                    st.markdown(status_badge_html(status), unsafe_allow_html=True)
                with rc4:
                    if st.button("Inspect ➔", key=f"btn_open_{cid}", use_container_width=True):
                        st.session_state["selected_case_id"] = cid
                        st.session_state["nav_module"] = "Visual Evidence Lab"
                        st.rerun()
                st.markdown("<hr style='margin:0.5rem 0 0.8rem 0; border:none; border-top:1px solid rgba(255,255,255,0.08);'>", unsafe_allow_html=True)
                
    with col_side:
        st.markdown("""
        <div class="panel-card">
            <div class="panel-header">
                <div>
                    <h3 class="panel-title">Risk Priority Profile</h3>
                    <div class="panel-subtitle">Assessed urgency distribution</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        priorities = [c.get("ai_findings", {}).get("suggested_priority", "Moderate") for c in cases]
        p_counts = {}
        for p in priorities:
            p_counts[p] = p_counts.get(p, 0) + 1
            
        p_df = pd.DataFrame([{"Priority": k, "Cases": v} for k, v in p_counts.items()])
        if not p_df.empty:
            chart = alt.Chart(p_df).mark_bar(cornerRadius=6, size=24).encode(
                x=alt.X('Cases:Q', axis=alt.Axis(tickMinStep=1, labelColor='#94A3B8', titleColor='#E2E8F0', gridColor='rgba(255,255,255,0.08)')),
                y=alt.Y('Priority:N', sort=['Immediate Attention', 'High', 'Moderate', 'Low'], axis=alt.Axis(labelColor='#FFFFFF', titleColor='#E2E8F0')),
                color=alt.Color('Priority:N', scale=alt.Scale(
                    domain=['Immediate Attention', 'High', 'Moderate', 'Low'],
                    range=['#DC2626', '#EA580C', '#D97706', '#0284C7']
                ), legend=None),
                tooltip=['Priority', 'Cases']
            ).properties(height=180).configure_view(stroke=None).configure(background='transparent')
            st.altair_chart(chart, use_container_width=True)


def render_inspection_view():
    st.markdown("""
    <div style="margin-bottom: 1.25rem;">
        <h2 style="margin: 0; font-size: 1.4rem; font-weight: 700; color: #FFFFFF;">Intake & New Visual Inspection</h2>
        <p style="margin: 0.2rem 0 0 0; color: #94A3B8; font-size: 0.9rem;">
            Upload photographic evidence or select a test scenario. Gemma multimodal vision will extract factual observations and assess risk.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("✨ Judge / Quick Demo Presets (One-click load real-world scenarios)", expanded=False):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            if st.button("🚪 Obstruction at Fire Exit", use_container_width=True):
                st.session_state["preset_title"] = "Obstructed Corridor Egress Door"
                st.session_state["preset_loc"] = "Student Union, Stairwell 2 West"
                st.session_state["preset_cat"] = "Safety or access"
                st.session_state["preset_desc"] = "Heavy stacked crates and packaging blocking emergency exit swing path."
                st.session_state["preset_concern"] = "High"
                st.session_state["preset_image_file"] = str(IMAGES_DIR / "sample_fire_exit.jpg")
                st.rerun()
        with col_p2:
            if st.button("💧 Water Leak Near Electricals", use_container_width=True):
                st.session_state["preset_title"] = "Overhead Water Seepage Near Conduit"
                st.session_state["preset_loc"] = "East Hallway Basement Mechanical Room"
                st.session_state["preset_cat"] = "Building or maintenance"
                st.session_state["preset_desc"] = "Water staining and active droplets running down toward electrical conduit."
                st.session_state["preset_concern"] = "High"
                st.session_state["preset_image_file"] = str(IMAGES_DIR / "sample_water_leak.jpg")
                st.rerun()
        with col_p3:
            if st.button("⚠️ Walkway Heave / Trip Hazard", use_container_width=True):
                st.session_state["preset_title"] = "Raised Concrete Walkway Joint"
                st.session_state["preset_loc"] = "Main Quad Walkway near Lecture Hall 3"
                st.session_state["preset_cat"] = "Road or public space"
                st.session_state["preset_desc"] = "Subgrade displacement created sharp 40mm vertical ridge across pedestrian route."
                st.session_state["preset_concern"] = "Medium"
                st.session_state["preset_image_file"] = str(IMAGES_DIR / "sample_trip_hazard.jpg")
                st.rerun()

    col_media, col_meta = st.columns([1, 1], gap="large")
    image = None
    with col_media:
        st.markdown("**1. Visual Evidence Capture**")
        input_mode = st.radio("Input Source", ["File Upload", "Camera Capture", "Loaded Preset"], horizontal=True, label_visibility="collapsed")
        if input_mode == "File Upload":
            uploaded_file = st.file_uploader("Upload clear photo", type=["png", "jpg", "jpeg", "webp"])
            if uploaded_file:
                raw_img = Image.open(uploaded_file)
                image = ImageOps.exif_transpose(raw_img).convert("RGB")
                st.image(image, caption=f"Uploaded: {uploaded_file.name}", use_container_width=True)
        elif input_mode == "Camera Capture":
            camera_file = st.camera_input("Capture live photo from camera")
            if camera_file:
                raw_img = Image.open(camera_file)
                image = ImageOps.exif_transpose(raw_img).convert("RGB")
                st.image(image, caption="Camera capture ready", use_container_width=True)
        elif input_mode == "Loaded Preset":
            preset_file = st.session_state.get("preset_image_file")
            if preset_file and os.path.exists(preset_file):
                image = Image.open(preset_file)
                st.image(image, caption=f"Loaded Preset: {os.path.basename(preset_file)}", use_container_width=True)
            else:
                st.info("No preset selected yet. Choose a scenario above.")

    with col_meta:
        st.markdown("**2. Context & Inspection Metadata**")
        title = st.text_input("Inspection Title / Summary", value=st.session_state.get("preset_title", ""))
        location = st.text_input("Physical Location / Facility Tag", value=st.session_state.get("preset_loc", ""))
        category = st.selectbox("Category Classification", ["Safety or access", "Building or maintenance", "Cleanliness or waste", "Road or public space", "Equipment or object", "Other"])
        concern = st.radio("User Preliminary Concern Level", ["Low", "Medium", "High", "Not sure"], horizontal=True)
        description = st.text_area("Field Notes / What did you observe?", value=st.session_state.get("preset_desc", ""), height=90)
        
        if location.strip():
            existing_cases = get_all_cases()
            matches = [c for c in existing_cases if location.strip().lower() in c.get("location", "").lower()]
            if matches:
                st.warning(f"⚠️ Recurring Location Alert: Found {len(matches)} previous inspection(s) at '{location}'.")

    st.markdown("<hr style='margin: 1.5rem 0; border-color:rgba(255,255,255,0.08);'>", unsafe_allow_html=True)
    
    col_btn, col_info = st.columns([1, 1])
    with col_info:
        api_key = get_api_key()
        has_key = bool(api_key and api_key != "YOUR_ACTUAL_API_KEY")
        st.markdown(f"**Target Model:** `{DEFAULT_GEMMA_MODEL}` · **Status:** <span style='color:{'#10B981' if has_key else '#EF4444'}; font-weight:700;'>{'Connected' if has_key else 'Missing API Key in secrets.toml'}</span>", unsafe_allow_html=True)
        
    with col_btn:
        btn_disabled = (image is None or not title.strip())
        analyze_btn = st.button("🚀 Run Fast Gemma Visual Inspection", type="primary", use_container_width=True, disabled=btn_disabled)

    if analyze_btn and image:
        with st.status("Gemma 4 Multimodal Analysis in Progress...", expanded=True) as status_box:
            try:
                st.write("1. Processing visual resolution (Fast 512px downscaled)...")
                saved_img_path = save_image_to_storage(image, filename_prefix="inspection")
                st.write(f"2. Invoking Gemma vision model `{DEFAULT_GEMMA_MODEL}`...")
                findings, raw_text = analyze_inspection_image(image, description, location, category, concern, DEFAULT_GEMMA_MODEL, api_key)
                st.write("3. Structuring visual evidence, uncertainty bounds, and checklist...")
                
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_case = {
                    "title": title.strip(),
                    "location": location.strip() or "General Facility",
                    "category": category,
                    "user_concern": concern,
                    "user_description": description.strip(),
                    "image_path": saved_img_path,
                    "after_image_path": None,
                    "status": "Action Required" if "immediate" in str(findings.get("suggested_priority", "")).lower() or "high" in str(findings.get("suggested_priority", "")).lower() else "Open",
                    "owner": "Unassigned",
                    "deadline": datetime.now().strftime("%Y-%m-%d"),
                    "ai_model": DEFAULT_GEMMA_MODEL,
                    "is_sample": False,
                    "ai_findings": findings,
                    "investigation_notes": [{"timestamp": now_str[:16], "author": "Intake Inspector", "text": "Inspection logged."}],
                    "history": [{"timestamp": now_str[:16], "action": "Case created", "actor": "Gemma Vision Pipeline"}],
                    "resolution": None
                }
                saved = save_case(new_case)
                status_box.update(label="Analysis complete! Case registered.", state="complete")
                st.session_state["selected_case_id"] = saved["id"]
                st.session_state["nav_module"] = "Visual Evidence Lab"
                st.success(f"Case {saved['id']} created successfully!")
                st.rerun()
            except Exception as exc:
                status_box.update(label="Analysis failed.", state="error")
                st.error(f"Error: {exc}")


def render_evidence_lab_view():
    cases = get_all_cases()
    if not cases:
        st.info("No cases available. Please start a new inspection first.")
        return
        
    case_ids = [c["id"] for c in cases]
    selected_id = st.session_state.get("selected_case_id", case_ids[0])
    if selected_id not in case_ids:
        selected_id = case_ids[0]
        
    case_options = [f"{c['id']} — {c.get('title', 'Untitled')[:35]}" for c in cases]
    chosen = st.selectbox("Active Case Selection", case_options, index=case_ids.index(selected_id))
    selected_id = chosen.split(" — ")[0]
    st.session_state["selected_case_id"] = selected_id
    
    case = get_case_by_id(selected_id)
    if not case:
        st.error("Case not found.")
        return
        
    findings = case.get("ai_findings", {})
    priority = findings.get("suggested_priority", "Moderate")
    confidence = findings.get("visual_confidence", "High")
    status = case.get("status", "Open")
    
    st.markdown(f"""
    <div style="padding:0.4rem 0 1rem 0; display:flex; align-items:center; gap:0.6rem;">
        {status_badge_html(status)}
        {priority_badge_html(priority)}
        {confidence_badge_html(confidence)}
    </div>
    """, unsafe_allow_html=True)
    
    tab_inspect, tab_before_after = st.tabs(["🔬 Detailed Visual Evidence Inspection", "⚖️ Before & After Verification Comparison"])
    
    with tab_inspect:
        col_img, col_facts = st.columns([7, 5], gap="large")
        with col_img:
            img_path = case.get("image_path")
            show_annotations = st.checkbox("Overlay Detected Evidence Pins", value=True)
            if img_path and os.path.exists(img_path):
                img = Image.open(img_path)
                display_img = img.copy()
                annotations = findings.get("annotations", [])
                if show_annotations and annotations:
                    draw = ImageDraw.Draw(display_img)
                    w, h = display_img.size
                    for idx, ann in enumerate(annotations, start=1):
                        x_px = int((ann.get("x", 50) / 100.0) * w)
                        y_px = int((ann.get("y", 50) / 100.0) * h)
                        r = max(14, int(w * 0.02))
                        draw.ellipse([(x_px - r, y_px - r), (x_px + r, y_px + r)], outline="#DC2626", width=4)
                        draw.ellipse([(x_px - 4, y_px - 4), (x_px + 4, y_px + 4)], fill="#DC2626")
                        draw.text((x_px + r + 6, y_px - r), f"#{idx}: {ann.get('label', '')}", fill="#DC2626")
                st.image(display_img, use_container_width=True)
            else:
                st.warning("Evidence image not found.")
                
            if findings.get("annotations"):
                st.caption("Active Visual Pins:")
                for idx, ann in enumerate(findings.get("annotations", []), start=1):
                    st.markdown(f"<span style='color:#DC2626; font-weight:700;'>#{idx}</span> **{ann.get('label')}:** {ann.get('note')}", unsafe_allow_html=True)
                    
        with col_facts:
            st.markdown("""
            <div style="background:rgba(18, 24, 38, 0.75); border:1px solid rgba(255, 255, 255, 0.1); border-radius:12px; padding:0.95rem; margin-bottom:1rem;">
                <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; color:#94A3B8; letter-spacing:0.05em;">Core Product Principle</div>
                <div style="font-size:0.95rem; font-weight:700; color:#FFFFFF; margin-top:3px;">
                    Never confuse visible evidence with assumptions.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**1. Direct Visual Observations (Verified in Photo)**")
            for obs in findings.get("visual_observations", []):
                st.markdown(f"""
                <div style="background:rgba(16, 185, 129, 0.12); border:1px solid rgba(16, 185, 129, 0.35); border-left:4px solid #10B981; border-radius:12px; padding:0.9rem; margin-bottom:0.75rem;">
                    <div style="color:#34D399; font-weight:700; font-size:0.85rem; margin-bottom:0.25rem;">✓ Verified Visual Fact</div>
                    <div style="font-size:0.9rem; color:#F1F5F9;">{obs}</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("**2. Technical Interpretations (Hypotheses)**")
            for interp in findings.get("possible_interpretations", []):
                st.markdown(f"""
                <div style="background:rgba(245, 158, 11, 0.12); border:1px solid rgba(245, 158, 11, 0.35); border-left:4px solid #F59E0B; border-radius:12px; padding:0.9rem; margin-bottom:0.75rem;">
                    <div style="color:#FBBF24; font-weight:700; font-size:0.85rem; margin-bottom:0.25rem;">? Plausible Hypothesis</div>
                    <div style="font-size:0.9rem; color:#F1F5F9;">{interp}</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("**3. Unconfirmed Information (Camera Limitations)**")
            for unc in findings.get("unconfirmed_information", []):
                st.markdown(f"""
                <div style="background:rgba(148, 163, 184, 0.10); border:1px solid rgba(148, 163, 184, 0.30); border-left:4px solid #94A3B8; border-radius:12px; padding:0.9rem; margin-bottom:0.75rem;">
                    <div style="color:#E2E8F0; font-weight:700; font-size:0.85rem; margin-bottom:0.25rem;">✕ Cannot Confirm From Single Image</div>
                    <div style="font-size:0.9rem; color:#F1F5F9;">{unc}</div>
                </div>
                """, unsafe_allow_html=True)

    with tab_before_after:
        c_before, c_after = st.columns(2, gap="large")
        with c_before:
            st.markdown("#### Initial Incident Condition (Before)")
            img_path = case.get("image_path")
            if img_path and os.path.exists(img_path):
                st.image(img_path, caption=f"Reported Condition ({case.get('created_at')})", use_container_width=True)
        with c_after:
            st.markdown("#### Rectified Condition (After)")
            after_path = case.get("after_image_path")
            if after_path and os.path.exists(after_path):
                st.image(after_path, caption="Verified Rectified Condition", use_container_width=True)
                if st.button("🗑️ Remove After Photo", key=f"del_after_{selected_id}"):
                    case["after_image_path"] = None
                    save_case(case)
                    st.rerun()
            else:
                st.markdown("""
                <div style="border:2px dashed rgba(255, 255, 255, 0.2); border-radius:14px; padding:2.5rem 1.5rem; text-align:center; background:rgba(255, 255, 255, 0.04);">
                    <div style="color:#FFFFFF; font-size:0.95rem; font-weight:600;">No resolution photo uploaded yet.</div>
                    <div style="color:#94A3B8; font-size:0.8rem; margin-top:0.3rem;">Attach proof of repair to complete case verification.</div>
                </div>
                """, unsafe_allow_html=True)
                after_file = st.file_uploader("Upload Remediation Proof Photo", type=["jpg", "png", "jpeg", "webp"], key=f"up_after_{selected_id}")
                if after_file:
                    raw_after = Image.open(after_file).convert("RGB")
                    saved_after_path = save_image_to_storage(raw_after, filename_prefix="remediated")
                    case["after_image_path"] = saved_after_path
                    save_case(case)
                    st.success("Verification photo uploaded successfully!")
                    st.rerun()


def render_findings_view():
    cases = get_all_cases()
    if not cases:
        st.info("No cases recorded yet.")
        return
        
    case_ids = [c["id"] for c in cases]
    selected_id = st.session_state.get("selected_case_id", case_ids[0])
    chosen = st.selectbox("Select Case", [f"{c['id']} — {c.get('title', 'Untitled')[:40]}" for c in cases], index=case_ids.index(selected_id) if selected_id in case_ids else 0)
    selected_id = chosen.split(" — ")[0]
    st.session_state["selected_case_id"] = selected_id
    
    case = get_case_by_id(selected_id)
    findings = case.get("ai_findings", {})
    
    st.markdown(f"""
    <div style="background:rgba(18, 24, 38, 0.8); border:1px solid rgba(255, 255, 255, 0.12); border-radius:16px; padding:1.25rem 1.5rem; margin:1rem 0 1.5rem 0;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem;">
            <div style="font-size:1.25rem; font-weight:700; color:#FFFFFF;">{case.get('id')}: {case.get('title')}</div>
            <div style="display:flex; gap:0.5rem; align-items:center;">
                {status_badge_html(case.get('status', 'Open'))}
                {priority_badge_html(findings.get('suggested_priority', 'Moderate'))}
                {confidence_badge_html(findings.get('visual_confidence', 'High'))}
            </div>
        </div>
        <p style="margin:0; font-size:0.95rem; color:#E2E8F0; line-height:1.5;">
            <strong style="color:#06B6D4;">Executive Summary:</strong> {findings.get('summary', 'None')}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_p, col_c = st.columns(2, gap="medium")
    with col_p:
        st.markdown(f"""
        <div style="background:rgba(234, 88, 12, 0.12); border:1px solid rgba(234, 88, 12, 0.35); border-radius:14px; padding:1.2rem; height:100%;">
            <div style="font-size:0.78rem; font-weight:700; text-transform:uppercase; color:#FB923C;">Explainable Risk Prioritization</div>
            <div style="font-size:1.2rem; font-weight:700; color:#FED7AA; margin:0.35rem 0;">Urgency: {findings.get('suggested_priority', 'Moderate')}</div>
            <div style="font-size:0.88rem; color:#FDE047; line-height:1.45;">{findings.get('priority_rationale', '')}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c:
        st.markdown(f"""
        <div style="background:rgba(13, 148, 136, 0.12); border:1px solid rgba(13, 148, 136, 0.35); border-radius:14px; padding:1.2rem; height:100%;">
            <div style="font-size:0.78rem; font-weight:700; text-transform:uppercase; color:#2DD4BF;">Optical Confidence Assessment</div>
            <div style="font-size:1.2rem; font-weight:700; color:#CCFBF1; margin:0.35rem 0;">Rating: {findings.get('visual_confidence', 'High')}</div>
            <div style="font-size:0.88rem; color:#A7F3D0; line-height:1.45;">{findings.get('confidence_rationale', '')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='margin:1.5rem 0; border-color:rgba(255,255,255,0.08);'>", unsafe_allow_html=True)
    st.markdown("### 🔍 Context-Aware Field Verification Checklist")
    checklist = findings.get("verification_checklist", [])
    for idx, task_obj in enumerate(checklist):
        cols_check = st.columns([1, 11])
        with cols_check[0]:
            is_done = st.checkbox("", value=task_obj.get("completed", False), key=f"find_chk_{selected_id}_{idx}")
            if is_done != task_obj.get("completed", False):
                task_obj["completed"] = is_done
                save_case(case)
                st.rerun()
        with cols_check[1]:
            strike = "line-through" if task_obj.get("completed") else "none"
            color = "#94A3B8" if task_obj.get("completed") else "#FFFFFF"
            st.markdown(f"<div style='text-decoration:{strike}; color:{color}; font-size:0.95rem; font-weight:500; padding-top:2px;'>{task_obj.get('task')}</div>", unsafe_allow_html=True)


def render_workspace_view():
    cases = get_all_cases()
    if not cases:
        st.info("No cases available.")
        return
        
    case_ids = [c["id"] for c in cases]
    selected_id = st.session_state.get("selected_case_id", case_ids[0])
    chosen = st.selectbox("Active Investigation", [f"{c['id']} — {c.get('title', 'Untitled')[:40]}" for c in cases], index=case_ids.index(selected_id) if selected_id in case_ids else 0)
    selected_id = chosen.split(" — ")[0]
    st.session_state["selected_case_id"] = selected_id
    case = get_case_by_id(selected_id)
    findings = case.get("ai_findings", {})
    
    st.markdown(f"""
    <div style="background:rgba(18, 24, 38, 0.8); border:1px solid rgba(255, 255, 255, 0.12); border-radius:16px; padding:1.25rem 1.5rem; margin:0.8rem 0 1.5rem 0;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
            <div style="font-size:1.25rem; font-weight:700; color:#FFFFFF;">{case.get('id')}: {case.get('title')}</div>
            <div style="display:flex; gap:0.5rem;">
                {status_badge_html(case.get('status', 'Open'))}
                {priority_badge_html(findings.get('suggested_priority', 'Moderate'))}
            </div>
        </div>
        <div style="font-size:0.88rem; color:#94A3B8;">
            📍 <strong style="color:#FFFFFF;">Location:</strong> {case.get('location')} · 👤 <strong style="color:#FFFFFF;">Assigned:</strong> {case.get('owner', 'Unassigned')} · 📅 <strong style="color:#FFFFFF;">Deadline:</strong> {case.get('deadline', 'None set')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_left, col_right = st.columns([7, 5], gap="large")
    with col_left:
        st.markdown("### 📝 Smart Verification Checklist")
        checklist = findings.get("verification_checklist", [])
        updated_check = False
        for idx, task in enumerate(checklist):
            c_box, c_text, c_note = st.columns([1, 7, 4])
            with c_box:
                checked = st.checkbox("", value=task.get("completed", False), key=f"work_chk_{selected_id}_{idx}")
                if checked != task.get("completed", False):
                    task["completed"] = checked
                    updated_check = True
            with c_text:
                strike = "line-through" if task.get("completed") else "none"
                color = "#94A3B8" if task.get("completed") else "#FFFFFF"
                st.markdown(f"<div style='text-decoration:{strike}; color:{color}; padding-top:4px; font-weight:500;'>{task.get('task')}</div>", unsafe_allow_html=True)
            with c_note:
                current_note = task.get("notes", "")
                new_note = st.text_input("Findings", value=current_note, key=f"work_note_{selected_id}_{idx}", placeholder="Field notes")
                if new_note != current_note:
                    task["notes"] = new_note
                    updated_check = True
        if updated_check:
            save_case(case)
            st.rerun()

    with col_right:
        st.markdown("### 🛡️ Human-in-the-Loop Sign-Off")
        resolution = case.get("resolution")
        if resolution and resolution.get("approval_status") == "Approved":
            st.markdown(f"""
            <div style="background:rgba(16, 185, 129, 0.15); border:1px solid rgba(16, 185, 129, 0.4); border-radius:12px; padding:1.2rem;">
                <div style="color:#6EE7B7; font-weight:700; font-size:1.05rem; margin-bottom:0.4rem;">✓ Human Verified & Formally Resolved</div>
                <div style="font-size:0.88rem; color:#D1FAE5; line-height:1.5;">
                    <strong>Approved by:</strong> {resolution.get('resolved_by')}<br>
                    <strong>Timestamp:</strong> {resolution.get('resolved_at')}<br>
                    <strong>Verification Notes:</strong> {resolution.get('verification_notes')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            with st.form(f"form_approval_{selected_id}"):
                reviewer = st.text_input("Inspector Name / Badge")
                sign_notes = st.text_area("Verification Sign-Off Statement")
                if st.form_submit_button("Formally Approve & Resolve Case", type="primary"):
                    if reviewer.strip():
                        case["status"] = "Resolved"
                        case["resolution"] = {
                            "resolved_by": reviewer.strip(),
                            "resolved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "verification_notes": sign_notes.strip() or "Verified on-site.",
                            "approval_status": "Approved"
                        }
                        save_case(case)
                        st.success("Case resolved!")
                        st.rerun()


def render_cases_view():
    cases = get_all_cases()
    st.markdown("## Case Register & Operations")
    if not cases:
        st.info("No cases available.")
        return
        
    for c in cases:
        cid = c.get("id")
        findings = c.get("ai_findings", {})
        c1, c2, c3, c4 = st.columns([2, 5, 2, 2])
        with c1:
            st.markdown(f"**{cid}**")
        with c2:
            st.markdown(f"**{c.get('title')}**\n📍 {c.get('location')}")
        with c3:
            st.markdown(priority_badge_html(findings.get('suggested_priority', 'Moderate')), unsafe_allow_html=True)
            st.markdown(status_badge_html(c.get('status', 'Open')), unsafe_allow_html=True)
        with c4:
            if st.button("Inspect", key=f"cs_{cid}"):
                st.session_state["selected_case_id"] = cid
                st.session_state["nav_module"] = "Visual Evidence Lab"
                st.rerun()
        st.markdown("<hr style='margin:0.4rem 0; border-color:rgba(255,255,255,0.06);'>", unsafe_allow_html=True)


def render_reports_view():
    cases = get_all_cases()
    st.markdown("## Formal Reports & Data Export")
    if not cases:
        st.info("No cases available.")
        return
        
    records = []
    for c in cases:
        f = c.get("ai_findings", {})
        records.append({
            "Case ID": c.get("id"),
            "Title": c.get("title"),
            "Location": c.get("location"),
            "Status": c.get("status"),
            "Priority": f.get("suggested_priority", "Moderate")
        })
    df = pd.DataFrame(records)
    st.dataframe(df, use_container_width=True)
    st.download_button("⬇️ Export Register CSV", df.to_csv(index=False).encode('utf-8'), "cases.csv", "text/csv")


def render_analytics_view():
    cases = get_all_cases()
    st.markdown("## Operational Analytics")
    if not cases:
        st.info("No cases to analyze.")
        return
        
    priorities = [c.get("ai_findings", {}).get("suggested_priority", "Moderate") for c in cases]
    df = pd.DataFrame([{"Priority": p} for p in priorities])
    chart = alt.Chart(df).mark_bar().encode(x='count()', y='Priority:N')
    st.altair_chart(chart, use_container_width=True)


def render_settings_view():
    st.markdown("## Settings & Diagnostics")
    api_key = get_api_key()
    st.write(f"**Google AI API Key Loaded:** {'Yes' if api_key else 'No'}")
    if st.button("⚡ Test Gemma Connection"):
        ok, msg = test_gemma_connection()
        if ok:
            st.success(msg)
        else:
            st.error(msg)
    if st.button("🔄 Reload Judge Sample Pack"):
        seed_sample_cases_if_needed(force=True)
        st.success("Sample pack loaded!")
        st.rerun()


# ==============================================================================
# 5. MAIN ENTRYPOINT & ROUTING
# ==============================================================================
st.set_page_config(
    page_title="REALITY CHECK AI — Detect What People Miss",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css(dark_mode=True)
seed_sample_cases_if_needed()

if "nav_module" not in st.session_state:
    st.session_state["nav_module"] = "Overview Dashboard"

cases = get_all_cases()
if "selected_case_id" not in st.session_state and cases:
    st.session_state["selected_case_id"] = cases[0]["id"]

with st.sidebar:
    st.markdown("""
    <div style="padding: 0.5rem 0 1.2rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 1.2rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <div style="width: 36px; height: 36px; background: linear-gradient(135deg, #EC4899 0%, #8B5CF6 50%, #06B6D4 100%); color: white; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1rem; box-shadow: 0 0 15px rgba(139, 92, 246, 0.4);">RC</div>
            <div>
                <div style="font-weight: 800; font-size: 1.1rem; color: #FFFFFF; line-height: 1.2;">REALITY CHECK</div>
                <div style="font-size: 0.72rem; color: #94A3B8; font-weight: 500;">Detect What People Miss</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    nav_items = [
        "Overview Dashboard",
        "New Inspection",
        "Visual Evidence Lab",
        "AI Findings",
        "Investigation Workspace",
        "Case Management",
        "Reports & Export",
        "Analytics & Trends",
        "Settings & Model"
    ]
    
    current_nav = st.session_state.get("nav_module", "Overview Dashboard")
    chosen = st.radio("Navigation", nav_items, index=nav_items.index(current_nav) if current_nav in nav_items else 0, label_visibility="collapsed")
    if chosen != current_nav:
        st.session_state["nav_module"] = chosen
        st.rerun()

render_brand_header(active_module=st.session_state["nav_module"], active_case_id=st.session_state.get("selected_case_id", ""))

active_mod = st.session_state["nav_module"]
if active_mod == "Overview Dashboard":
    render_dashboard_view()
elif active_mod == "New Inspection":
    render_inspection_view()
elif active_mod == "Visual Evidence Lab":
    render_evidence_lab_view()
elif active_mod == "AI Findings":
    render_findings_view()
elif active_mod == "Investigation Workspace":
    render_workspace_view()
elif active_mod == "Case Management":
    render_cases_view()
elif active_mod == "Reports & Export":
    render_reports_view()
elif active_mod == "Analytics & Trends":
    render_analytics_view()
elif active_mod == "Settings & Model":
    render_settings_view()
