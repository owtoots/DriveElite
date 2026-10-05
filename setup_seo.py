import os
import shutil
import streamlit as st

# 1. Locate Streamlit's core files inside Render
streamlit_dir = os.path.dirname(st.__file__)
static_dir = os.path.join(streamlit_dir, "static")
index_path = os.path.join(static_dir, "index.html")
streamlit_favicon = os.path.join(static_dir, "favicon.png")

# 2. THE FAVICON KILLER: Overwrite Streamlit's logo with yours
# This prevents the Streamlit logo from ever flashing during page load
if os.path.exists("logo.png"):
    shutil.copyfile("logo.png", streamlit_favicon)
    print("✅ Successfully overwrote Streamlit favicon!")

# 3. Read the original background HTML
with open(index_path, "r", encoding="utf-8") as f:
    html = f.read()

# REPLACE THIS LINK with your public image host link (e.g., Postimages/ImgBB)
# If you don't have one, this GitHub link might work, but a public host is safer.
logo_url = "https://i.postimg.cc/abc12345/logo.png"

# 4. Inject the SEO tags for a massive social media preview card
meta_tags = f"""
    <!-- Custom DriveElite Meta Tags -->
    <meta property="og:title" content="DriveElite | Peer-to-Peer Car Rentals" />
    <meta property="og:description" content="Philippines' Premier Peer-to-Peer Car Sharing Platform" />
    <meta property="og:image" content="{logo_url}" />
    <meta property="og:url" content="https://driveelite.ph" />
    <meta name="twitter:card" content="summary_large_image" />
    <title>DriveElite</title>
</head>
"""

# 5. Save the changes to the HTML
if "DriveElite Meta Tags" not in html:
    new_html = html.replace("</head>", meta_tags)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    print("✅ Successfully injected DriveElite SEO Meta Tags!")
else:
    print("⚠️ Meta tags already exist.")
