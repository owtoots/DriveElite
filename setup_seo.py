import os
import streamlit as st

# Locate the Streamlit installation folder inside Render's system
streamlit_dir = os.path.dirname(st.__file__)
index_path = os.path.join(streamlit_dir, "static", "index.html")

# Read the original HTML file
with open(index_path, "r", encoding="utf-8") as f:
    html = f.read()

# The raw GitHub link to your logo so Facebook/Viber can see it
logo_url = "https://i.postimg.cc/abc12345/logo.png"

# The "Open Graph" meta tags that social media apps look for
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

# Replace the default </head> with our custom tags
if "DriveElite Meta Tags" not in html:
    new_html = html.replace("</head>", meta_tags)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    print("✅ Successfully injected DriveElite SEO Meta Tags!")
else:
    print("⚠️ Meta tags already exist.")
