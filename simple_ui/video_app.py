import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import streamlit as st


class RateLimit:
    def __init__(self):
        self.last_request = 0
        self.min_interval = 120
        self.reset()

    def can_make_request(self) -> bool:
        now = time.time()
        if now - self.last_request >= self.min_interval:
            self.last_request = now
            return True
        return False

    def reset(self):
        self.last_request = 0


class APIClient:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()

    def make_request(
        self, endpoint: str, method: str = "GET", data: dict = None
    ) -> requests.Response:
        """Make secure API requests with retry and validation."""
        if endpoint == "generate" and not self.config.rate_limiter.can_make_request():
            raise ValueError("Please wait at least 3 minutes between video generations")

        try:
            url = f"{self.config.base_url}/imagine/{endpoint}"

            print(f"Making request to: {url}")
            print(f"Method: {method}")
            print(f"Data: {data}")

            if endpoint == "generate" and data:
                if data.get("num_frames", 0) < 8 or data.get("num_frames", 0) > 50:
                    raise ValueError("Number of frames must be between 8 and 50")
                if data.get("fps", 0) < 1 or data.get("fps", 0) > 61:
                    raise ValueError("FPS must be between 1 and 60")
                if (
                    data.get("guidance_scale", 0) < 1.0
                    or data.get("guidance_scale", 0) > 10.0
                ):
                    raise ValueError("Guidance scale must be between 1.0 and 10.0")
                if (
                    data.get("num_inference_steps", 0) < 1
                    or data.get("num_inference_steps", 0) > 50
                ):
                    raise ValueError(
                        "Number of inference steps must be between 1 and 50"
                    )

            response = self.session.request(
                method=method,
                url=url,
                headers={
                    "Authorization": f"Bearer {self.config.token}",
                    "Content-Type": "application/json",
                },
                json=data,
                timeout=180,
                verify=True,
            )

            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Full error details: {str(e)}")
            if hasattr(e, "response") and hasattr(e.response, "text"):
                print(f"Error response: {e.response.text}")
            raise ValueError(f"API request failed: {str(e)}")


class HistoryManager:
    def __init__(self, output_dir: Path):
        self.history_file = output_dir / "generation_history.json"
        self.max_history_size = 50

    def load(self) -> list:
        """Safely load history."""
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r") as f:
                history = json.load(f)
                return history[-self.max_history_size :]
        except (json.JSONDecodeError, IOError):
            return []

    def save(self, history: list):
        """save history."""
        temp_file = self.history_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as f:
                json.dump(history[-self.max_history_size :], f)
            temp_file.rename(self.history_file)
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise e


class VideoConfig:
    def __init__(self):
        self.base_url = "http://localhost:9000"
        self.output_dir = Path("generated_videos")
        self.output_dir.mkdir(exist_ok=True, mode=0o755)
        self.token = os.getenv("VALID_TOKEN")
        self.rate_limiter = RateLimit()
        self.api_client = APIClient(self)
        self.history_manager = HistoryManager(self.output_dir)
        self.rate_limiter.reset()
        if not self.token:
            raise ValueError("VALID_TOKEN environment variable not set")


def clean_prompt(prompt: str) -> str:
    """input sanitization."""
    if not prompt:
        return ""
    if len(prompt) > 500:
        raise ValueError("Prompt too long (max 500 characters)")
    cleaned = re.sub(r"[^a-zA-Z0-9\s.,!?-]", "", prompt)
    return " ".join(cleaned.split())


def get_model_info() -> Optional[dict]:
    """Fetch current model information from the API."""
    try:
        response = config.api_client.make_request("info")
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch model info: {e}")
        return None


def load_api_docs() -> str:
    """Load and format API documentation."""
    try:
        with open("api_docs.md", "r") as f:
            return f.read()
    except Exception:
        return "API documentation not available"


def format_token_display(token: str) -> str:
    """Securely format token display."""
    if not token:
        return ""
    return f"{token[:4]}...{token[-4:]}"


def copy_to_clipboard():
    """Handle token copying with feedback."""
    if config.token:  # Only copy if token exists
        st.session_state.clipboard = config.token
        st.session_state.token_copied = True


def display_history_entry(entry: dict):
    """Display a single history entry."""
    st.markdown('<div class="video-history-card">', unsafe_allow_html=True)
    st.markdown('<div class="video-container">', unsafe_allow_html=True)
    st.video(entry["path"], start_time=0)
    st.markdown("</div>", unsafe_allow_html=True)
    with st.expander(entry["prompt"][:50] + "..."):
        params = entry.get("parameters", {})
        st.code(
            f"""
Frames: {params.get('num_frames')}
FPS: {params.get('fps')}
Steps: {params.get('num_inference_steps')}
Guidance: {params.get('guidance_scale')}
Time: {datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M')}
        """
        )


def display_history(history: list, page_size: int = 9):
    """Display history with pagination."""
    if not history:
        st.info("No generation history yet.")
        return

    total_pages = len(history) // page_size + (1 if len(history) % page_size else 0)
    page = (
        st.select_slider("Page", options=range(1, total_pages + 1))
        if total_pages > 1
        else 1
    )
    start_idx = (page - 1) * page_size
    page_history = list(reversed(history[start_idx : start_idx + page_size]))
    cols = st.columns(3)
    for idx, entry in enumerate(page_history):
        with cols[idx % 3]:
            display_history_entry(entry)


def safe_save_video(video_path: Path, video_data: bytes):
    """Safely save video file."""
    try:
        temp_path = video_path.with_suffix(".tmp")
        with open(temp_path, "wb") as f:
            f.write(video_data)
        temp_path.rename(video_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise e


def main():
    st.set_page_config(
        page_title="Video Generation Demo on Intel XPUs",
        page_icon="🎥",
        layout="centered",
        initial_sidebar_state="auto",
    )
    st.markdown(
        """
        <style>
        /* Custom pink theme */
        :root {
            --font-main: 'Poppins', sans-serif;
            --font-code: 'JetBrains Mono', monospace;
        }

        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono&display=swap');

        /* Global styles */
        .stApp {
            background-color: var(--background-color);
            font-family: var(--font-main);
        }

        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            font-family: var(--font-main);
            color: var(--secondary-color);
            font-weight: 600;
        }

        /* Streamlit elements styling */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            border-radius: 10px;
            border: 2px solid var(--primary-color) !important;
        }

        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            box-shadow: 0 0 0 2px var(--secondary-color) !important;
        }

        /* Buttons */
        .stButton > button {
            font-family: var(--font-main);
            background-color: var(--primary-color) !important;
            color: white !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
        }

        .stButton > button:hover {
            background-color: var(--secondary-color) !important;
            box-shadow: 0 4px 8px rgba(255,20,147,0.3) !important;
            transform: translateY(-2px) !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab"] {
            font-family: var(--font-main);
            font-weight: 500;
        }

        .stTabs [data-baseweb="tab-list"] {
            background-color: white;
            border-radius: 10px;
            padding: 0.5rem;
        }

        .stTabs [aria-selected="true"] {
            background-color: var(--primary-color) !important;
            color: white !important;
        }

        /* Cards and containers */
        .stForm, .api-docs, .video-history-card {
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            background-color: white;
        }

        /* Code blocks */
        code {
            font-family: var(--font-code) !important;
            background-color: #f8f9fa;
            padding: 0.2em 0.4em;
            border-radius: 4px;
        }

        /* Slider and number input */
        .stSlider > div > div > div > div {
            background-color: var(--primary-color) !important;
        }

        .stNumberInput > div > div > input {
            border-color: var(--primary-color) !important;
        }

        /* Progress and loading indicators */
        .stProgress > div > div > div > div {
            background-color: var(--primary-color) !important;
        }

        /* Success/Info/Error messages */
        .stSuccess, .stInfo {
            border-left-color: var(--primary-color) !important;
        }

        /* Tooltips */
        .tooltip {
            background-color: var(--secondary-color) !important;
            color: white !important;
        }

        /* Animation for interactive elements */
        @keyframes glow {
            0% { box-shadow: 0 0 5px var(--primary-color); }
            100% { box-shadow: 0 0 20px var(--primary-color); }
        }

        .interactive-element:hover {
            animation: glow 1s ease-in-out infinite alternate;
        }

        /* Form submit button (Generate Video button) */
        button[type="submit"] {
            background-color: var(--primary-color) !important;
            color: white !important;
            border: none !important;
            padding: 0.75rem 2.5rem !important;
            font-size: 1.1rem !important;
            font-weight: bold !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            margin-top: 1rem !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
            border-radius: 8px !important;
        }

        button[type="submit"]:hover {
            background-color: var(--secondary-color) !important;
            box-shadow: 0 4px 8px rgba(255,20,147,0.6) !important;
            transform: translateY(-2px) !important;
        }

        /* Additional form styling */
        .stForm > form {
            background-color: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }

        /* Token button styling */
        .stButton button[kind="secondary"] {
            background-color: #FF1493 !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            font-size: 0.9rem !important;
            font-weight: 500 !important;
            height: 38px !important;
            margin-top: 0 !important;
            transform: translateY(-1px) !important;  /* Fine-tune alignment */
        }

        .stButton button[kind="secondary"]:hover {
            background-color: #FF69B4 !important;
            border: none !important;
        }

        /* Info box styling */
        .info-box {
            background-color: #e7f3ef;
            border-left: 4px solid #2e7d32;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        }

        .info-box p {
            color: #1e4620;
            margin: 0;
            padding: 0.2rem 0;
        }

        .info-box strong {
            color: #2e7d32;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<h1 class="title">🎥 Video Generation Demo on Intel XPUs</h1>',
        unsafe_allow_html=True,
    )
    tab1, tab2, tab3 = st.tabs(
        ["🎬 Video Generation", "📚 API Documentation", "🔑 Authentication"]
    )

    with tab1:
        model_info = get_model_info()
        if model_info:
            st.markdown(
                f'<div class="model-info">📌 Model: {model_info.get("model", "Unknown")}</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            "Generate videos using our API. For advanced options, check the API Documentation tab."
        )
        with st.form("generation_form"):
            prompt = st.text_area(
                "Enter your prompt:",
                height=100,
                help="Describe the video you want to generate",
            )
            col1, col2 = st.columns(2)
            with col1:
                max_frames = min(model_info.get("max_frames", 49), 49)
                num_frames = st.number_input(
                    "Number of frames",
                    min_value=8,
                    max_value=50,
                    value=24,
                    help="Must be between 8 and 50 frames",
                )
            with st.expander("⚙️ Advanced Configuration", expanded=False):
                adv_col1, adv_col2 = st.columns(2)
                with adv_col1:
                    inference_steps = st.number_input(
                        "Inference Steps", min_value=1, max_value=50, value=20
                    )
                    guidance_scale = st.number_input(
                        "Guidance Scale",
                        min_value=1.0,
                        max_value=10.0,
                        value=6.0,
                        step=0.5,
                    )
                with adv_col2:
                    fps = st.number_input("FPS", min_value=1, max_value=60, value=24)
            submitted = st.form_submit_button("Generate Video")
            if submitted:
                try:
                    if not prompt:
                        st.error("Please enter a prompt.")
                        return
                    cleaned_prompt = clean_prompt(prompt)
                    if not cleaned_prompt:
                        st.error("Invalid prompt after cleaning, please try again.")
                        return
                    params = {
                        "prompt": cleaned_prompt,
                        "num_frames": min(num_frames, max_frames),
                        "num_inference_steps": min(inference_steps, 50),
                        "guidance_scale": max(1.0, min(guidance_scale, 10.0)),
                        "fps": min(fps, 30),
                    }

                    with st.spinner("Generating video..."):
                        try:
                            response = config.api_client.make_request(
                                "generate", method="POST", data=params
                            )
                            video_data = response.content
                            timestamp = datetime.now().isoformat()
                            video_path = config.output_dir / f"video_{timestamp}.mp4"
                            safe_save_video(video_path, video_data)
                            history = config.history_manager.load()
                            history.append(
                                {
                                    "prompt": cleaned_prompt,
                                    "timestamp": timestamp,
                                    "path": str(video_path),
                                    "parameters": params,
                                }
                            )
                            config.history_manager.save(history)
                            st.success("Video generated successfully!")
                        except Exception as e:
                            st.error(f"Error during generation: {e}")
                except Exception as e:
                    st.error(f"Error during generation: {e}")
    with tab2:
        st.markdown("### 📚 API Documentation")
        st.markdown("Complete API documentation for advanced usage and integration.")
        api_docs = load_api_docs()
        st.markdown(f'<div class="api-docs">{api_docs}</div>', unsafe_allow_html=True)
    with tab3:
        st.markdown("### 🔑 Authentication")
        st.markdown("Your current authentication token:")
        st.markdown(
            """
            <style>
            .token-container {
                display: flex;
                align-items: flex-end;
                gap: 1rem;
            }
            .token-container .token-input {
                flex: 1;
            }
            .token-container .token-button {
                min-width: 100px;
            }
            </style>
        """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([6, 1])
        with col1:
            token_display = st.text_input(
                "Token:",
                value=(
                    config.token
                    if st.session_state.get("show_token", False)
                    else format_token_display(config.token)
                ),
                disabled=True,
                key="token_input",
                label_visibility="collapsed",
            )
        with col2:
            button_label = (
                "Hide" if st.session_state.get("show_token", False) else "Unhide"
            )
            if st.button(
                button_label,
                use_container_width=True,
                type="secondary",
                key="token_button",
            ):
                st.session_state.show_token = not st.session_state.get(
                    "show_token", False
                )
                st.rerun()

        st.markdown(
            """
        <div class="info-box">
            <p><strong>Note:</strong> This token is required for API requests. Click to copy when unhidden.</p>
            <p>See the API Documentation tab for usage examples.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="history-section">', unsafe_allow_html=True)
    st.markdown("### 📜 Generation History")
    history = config.history_manager.load()
    search_term = st.text_input("🔍 Search history by prompt")
    if search_term:
        history = [h for h in history if search_term.lower() in h["prompt"].lower()]
    display_history(history)
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    config = VideoConfig()
    main()
