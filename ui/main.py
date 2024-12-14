import streamlit as st
from video_generation import (
    AsyncVideoGenerator,
    generate_unique_filename,
    cleanup_old_videos,
)
from image_generation import ImageGenerator
from config import config, logger, output_dir
from style import apply_styles
from datetime import datetime
import time

video_generator = AsyncVideoGenerator()
image_generator = ImageGenerator()

DEFAULT_PROMPT = "A scenic Ghibli-style village"


def render_header():
    st.markdown(
        """
        <div class="header-container">
            <h1>🎥 Creative Studio</h1>
            <p>Transform your ideas into stunning videos or images using advanced AI and Intel GPU-powered cloud systems.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_video_input_section():
    with st.container():
        st.markdown("**Model:** CogVideoX")
        prompt = st.text_area(
            "Enter your video prompt",
            value=DEFAULT_PROMPT,
            placeholder="Example: A serene lake at sunset with mountains in the background",
        )

        col1, col2 = st.columns(2)
        with col1:
            num_frames = st.slider("Number of frames", 10, config.max_frames, 30)
        with col2:
            fps = st.slider("Frames per second", 1, config.max_fps, 30)

        return prompt, num_frames, fps


def render_image_input_section():
    with st.container():
        st.markdown("**Model:** Flux")
        prompt = st.text_area(
            "Enter your image prompt",
            value=DEFAULT_PROMPT,
            placeholder="Example: A magical cosmic unicorn",
        )

        num_variations = st.slider(
            "Number of variations (automatically enhance prompt)", 1, 100, 1
        )

        with st.expander("Advanced Options"):
            col1, col2, col3 = st.columns(3)
            with col1:
                img_size = st.selectbox("Image Size", [512, 768, 1024], index=2)
            with col2:
                guidance_scale = st.slider("Guidance Scale", 0, 20, 7)
            with col3:
                num_inference_steps = st.slider("Inference Steps", 1, 100, 50)

        return prompt, num_variations, img_size, guidance_scale, num_inference_steps


def display_previous_generations():
    if st.session_state.get("generated_items"):
        st.markdown(
            "<h2 style='margin-top: 2rem;'>Your Gallery</h2>", unsafe_allow_html=True
        )
        gallery_container = st.container()
        with gallery_container:
            cols = st.columns(len(st.session_state["generated_items"]))
            for idx, item in enumerate(st.session_state["generated_items"]):
                with cols[idx]:
                    if item["type"] == "video":
                        st.video(item["path"])
                    elif item["type"] == "image":
                        st.image(item["path"])
                    st.markdown(f"**Prompt:** {item['prompt']}")
                    st.markdown(f"*Generated on: {item['timestamp']}*")


def main():
    st.set_page_config(
        page_title="Creative Studio",
        page_icon="🎥",
        layout="wide",
    )
    apply_styles()

    # Initialize session state
    if "generated_items" not in st.session_state:
        st.session_state["generated_items"] = []

    if "is_generating" not in st.session_state:
        st.session_state["is_generating"] = False

    # Render UI
    render_header()
    mode = st.selectbox("Choose Generation Mode", ["Video", "Image"])

    if mode == "Video":
        prompt, num_frames, fps = render_video_input_section()

        if st.button("Generate Video", disabled=st.session_state["is_generating"]):
            if prompt:
                st.session_state["is_generating"] = True
                task_id = generate_unique_filename()
                video_generator.submit_task(task_id, prompt, num_frames, fps)

                # Progress display
                status_messages = [
                    "🎨 Preparing your video...",
                    "🎬 Creating frames...",
                    "✨ Adding final touches...",
                ]

                start_time = time.time()
                status_container = st.empty()
                result = None

                while not result:
                    elapsed_time = int(time.time() - start_time)
                    current_message = status_messages[
                        (elapsed_time // 5) % len(status_messages)
                    ]
                    status_container.markdown(f"**{current_message}**")
                    result = video_generator.get_result(task_id)
                    time.sleep(0.5)

                video_path = output_dir / task_id
                with open(video_path, "wb") as f:
                    f.write(result)

                cleanup_old_videos()

                st.session_state["generated_items"].append(
                    {
                        "type": "video",
                        "path": str(video_path),
                        "prompt": prompt,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

                st.success("Video generated successfully!")
                st.video(str(video_path))
                video_generator.clear_result(task_id)
                st.session_state["is_generating"] = False
            else:
                st.error("Please enter a prompt to generate a video.")

    elif mode == "Image":
        prompt, num_variations, img_size, guidance_scale, num_inference_steps = (
            render_image_input_section()
        )

        if st.button("Generate Images", disabled=st.session_state["is_generating"]):
            if prompt:
                st.session_state["is_generating"] = True
                progress_bar = st.progress(0)

                def update_progress(progress):
                    progress_bar.progress(progress)

                images = image_generator.generate_image_variations(
                    prompt, num_variations, progress_callback=update_progress
                )

                for idx, image_data in enumerate(images):
                    image_path = output_dir / f"image_{idx + 1}.png"
                    with open(image_path, "wb") as f:
                        f.write(image_data)

                    st.session_state["generated_items"].append(
                        {
                            "type": "image",
                            "path": str(image_path),
                            "prompt": f"{prompt} (variation {idx + 1})",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )

                    st.image(image_path)

                st.success("Images generated successfully!")
                st.session_state["is_generating"] = False
            else:
                st.error("Please enter a prompt to generate images.")

    display_previous_generations()


if __name__ == "__main__":
    main()
