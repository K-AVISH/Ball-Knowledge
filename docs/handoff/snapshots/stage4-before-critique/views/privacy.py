"""Privacy policy page. Describes what this application actually does with data."""
import streamlit as st

import config
import ui

ui.page_header("Privacy policy", f"Last updated {config.LEGAL_LAST_UPDATED}.")

if not (config.OPERATOR_NAME and config.CONTACT_EMAIL):
    st.warning(
        "Before launch: set OPERATOR_NAME and CONTACT_EMAIL in config.py. "
        "This notice disappears once both are set."
    )

contact = (
    f"{config.OPERATOR_NAME} can be reached at {config.CONTACT_EMAIL}."
    if config.OPERATOR_NAME and config.CONTACT_EMAIL
    else "Contact details are not set yet."
)

st.markdown(
    f"""
<div class="legal">

<h2>Summary</h2>
<p>Ball Knowledge Vision AI recognises hand gestures from your webcam. It has no user accounts,
no advertising and no analytics. Video from your camera is processed in memory and is never
saved. The only thing that can be stored is a set of numbers describing hand landmarks, and
only when you press Start recording on the Data collector page.</p>

<h2>How the camera is used</h2>
<p>When you press Start camera, your browser sends video frames to the application over a
WebRTC connection. The application finds hand landmarks in each frame, draws them on the
preview and discards the frame. When the application runs on your own computer, the video
never leaves it. When the application is opened through a web address, the frames travel
over the internet to the server running it, where they are processed in memory and not
stored. You can stop the camera at any time with the Stop camera button, and you can revoke
camera permission in your browser settings.</p>

<h2>What is saved</h2>
<p>Only when you start a recording, each sample saved to <code>data/samples.csv</code>
contains:</p>
<ul>
<li>numbers that describe the positions of landmarks on your hand, scaled so that they do not
depend on where the hand is in the frame;</li>
<li>the gesture label you chose;</li>
<li>a random recording identifier and a timestamp;</li>
<li>the name you typed in the optional "Recorded by" field, if any.</li>
</ul>
<p>These numbers are not images or video, but they do describe the shape of your hand, so treat
the file as personal data. A trained model file derived from the samples is stored in the
<code>models</code> folder. Frames in which no hand is found are not saved.</p>

<h2>Network connections</h2>
<ul>
<li>To set up the camera connection, the browser and the application use a public STUN
server operated by Google (<code>stun.l.google.com</code>) unless a different server is
configured. A STUN server can see the public IP address of the device that contacts it.
No video is sent to it.</li>
<li>During installation, <code>download_models.py</code> downloads the MediaPipe model files
from <code>storage.googleapis.com</code>, and <code>pip</code> downloads packages from PyPI.</li>
<li>Streamlit usage statistics are switched off in <code>.streamlit/config.toml</code>.</li>
</ul>

<h2>Cookies and browser storage</h2>
<p>Streamlit sets a first-party cookie for protection against cross-site request forgery and
keeps session information in your browser while the page is open. This application adds no
advertising or analytics cookies.</p>

<h2>Your choices and deleting data</h2>
<p>On the Data collector page, open Manage data to undo your last recording or delete every
sample of a gesture. You can also delete <code>data/samples.csv</code> and the files in the
<code>models</code> folder directly. If you recorded another person, delete their samples on
request.</p>

<h2>Changes to this policy</h2>
<p>If the application changes how it handles data, this page is updated and the date above
changes.</p>

<h2>Contact</h2>
<p>{contact}</p>

</div>
""",
    unsafe_allow_html=True,
)
