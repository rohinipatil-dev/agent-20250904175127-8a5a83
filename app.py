import streamlit as st
from openai import OpenAI
import requests
from urllib.parse import urlparse


# --------------- Utility Functions ---------------

def normalize_url(url: str) -> str:
    """Trim and ensure the URL has a scheme."""
    if not url:
        return ""
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    return url


def is_presentations_ai_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return "presentations.ai" in (parsed.netloc or "")
    except Exception:
        return False


def check_url_accessibility(url: str, timeout: int = 10):
    """
    Try to access the URL and return a dict with status information.
    """
    info = {
        "ok": False,
        "status_code": None,
        "final_url": None,
        "requires_auth": None,
        "error": None,
    }
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; StreamlitApp/1.0)"
        }
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        info["status_code"] = resp.status_code
        info["final_url"] = resp.url

        # Heuristics to detect sign-in walls or restricted access
        text_lower = (resp.text or "").lower()
        auth_markers = ["sign in", "log in", "login", "unauthorized", "permission", "request access"]
        requires_auth = any(m in text_lower for m in auth_markers)

        info["requires_auth"] = requires_auth
        info["ok"] = resp.status_code == 200 and not requires_auth
        return info
    except Exception as e:
        info["error"] = str(e)
        return info


def generate_ai_instructions(client: OpenAI, url: str, accessibility_info: dict) -> str:
    """
    Use GPT-4 to generate succinct steps to create a publicly accessible/global link.
    """
    status_summary = []
    if accessibility_info.get("status_code") is not None:
        status_summary.append(f"HTTP status: {accessibility_info['status_code']}")
    if accessibility_info.get("requires_auth") is True:
        status_summary.append("Appears to require sign-in")
    elif accessibility_info.get("requires_auth") is False:
        status_summary.append("No sign-in required")
    if accessibility_info.get("error"):
        status_summary.append(f"Error: {accessibility_info['error']}")

    status_text = "; ".join(status_summary) if status_summary else "No status available"

    user_prompt = f"""
You are assisting a user who wants a global/public share link for a Presentations.ai deck.

Deck URL:
{url}

Observed link status:
{status_text}

Write clear, concise, step-by-step instructions (5-8 steps) to:
- Make the deck publicly accessible (no login required) using the Presentations.ai UI.
- Copy the public link.
- Verify access in an incognito window.
- Include a brief note about revoking access later if needed.

If the link already appears publicly accessible, explicitly state that it can be used as-is, then still include quick verification steps.
Avoid fabricating product features—use generic, widely-used “Share”/“Anyone with the link can view” language.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return (
            "AI instructions unavailable. Reason: "
            + str(e)
            + "\n\nFallback steps:\n"
            "- Open the deck in Presentations.ai\n"
            "- Click Share (or similar)\n"
            "- Set visibility to Public or Anyone with the link can view\n"
            "- Copy the link\n"
            "- Test in an incognito/private window\n"
            "- Revoke or restrict access later via the same Share settings"
        )


# --------------- Streamlit UI ---------------

def main():
    st.set_page_config(page_title="Global Link for Presentations.ai Deck", page_icon="🌐", layout="centered")
    st.title("Global Link Generator for Presentations.ai")
    st.write("Paste your Presentations.ai deck URL to generate and verify a global (public) link.")

    default_url = "https://app.presentations.ai/view/yfVgRnply2"
    url_input = st.text_input("Deck URL", value=default_url, placeholder="https://app.presentations.ai/view/...", help="Use the 'view' link from Presentations.ai")

    generate = st.button("Generate Global Link")

    if generate:
        url = normalize_url(url_input)

        if not url:
            st.error("Please provide a deck URL.")
            return

        if not is_presentations_ai_url(url):
            st.warning("This doesn't look like a Presentations.ai URL. Proceeding anyway, but results may vary.")

        with st.spinner("Checking link accessibility..."):
            access_info = check_url_accessibility(url)

        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Your Global Link")
            st.text_input("Copyable link", value=url, disabled=True)
            st.write(f"Open link: {url}")

        with col2:
            if access_info.get("ok"):
                st.success("Publicly accessible")
            else:
                if access_info.get("error"):
                    st.warning("Could not verify. Network error occurred.")
                elif access_info.get("status_code") == 200 and access_info.get("requires_auth") is True:
                    st.warning("Link may require sign-in. Update share settings to make it public.")
                elif access_info.get("status_code") and access_info.get("status_code") != 200:
                    st.warning(f"Link responded with status {access_info.get('status_code')}. May not be public.")
                else:
                    st.info("Verification inconclusive. Please test in an incognito window.")

        # AI guidance
        st.markdown("---")
        st.subheader("How to make the link public (AI-guided steps)")
        with st.spinner("Generating AI instructions..."):
            client = OpenAI()
            guidance = generate_ai_instructions(client, url, access_info)
        st.write(guidance)

        # Verification tips
        with st.expander("Manual verification tips"):
            st.write(
                "- Open the link in an incognito/private window and on a mobile device.\n"
                "- Ensure it doesn't prompt for sign-in or access request.\n"
                "- Share the link with a colleague outside your workspace to confirm."
            )

        st.markdown("---")
        st.caption("Note: This tool cannot change your presentation's privacy settings. Use the Share settings inside Presentations.ai to make the deck public.")


if __name__ == "__main__":
    main()