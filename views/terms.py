"""Terms and conditions page."""
import streamlit as st

import config
import ui

ui.page_header("Terms and conditions", f"Last updated {config.LEGAL_LAST_UPDATED}.")

if not (config.OPERATOR_NAME and config.CONTACT_EMAIL):
    st.warning(
        "Before launch: set OPERATOR_NAME and CONTACT_EMAIL in config.py, and GOVERNING_LAW "
        "if you want a governing law clause. This notice disappears once the first two are set."
    )

operator = config.OPERATOR_NAME or "the operator of this site"
contact = (
    f"Questions about these terms can be sent to {config.CONTACT_EMAIL}."
    if config.CONTACT_EMAIL
    else "Contact details are not set yet."
)
governing = (
    f"<h2>Governing law</h2><p>These terms are governed by {config.GOVERNING_LAW}.</p>"
    if config.GOVERNING_LAW
    else ""
)

st.markdown(
    f"""
<div class="legal">

<h2>About this service</h2>
<p>Ball Knowledge Vision AI, provided by {operator}, recognises hand gestures from a webcam
using a model trained on samples you record, and shows images and descriptions that you
configure. By using it you agree to these terms.</p>

<h2>Using the camera and recording people</h2>
<p>Only turn on the camera and record samples when you are entitled to do so. If another
person appears in the camera or their gestures are recorded, you must have their permission.
Do not use the service to monitor or identify people. How data is handled is described in the
<a href="/privacy" target="_self">privacy policy</a>.</p>

<h2>Your content</h2>
<p>You keep ownership of the samples, images, titles and descriptions you add. You confirm that
you have the right to use every image you add, that it does not infringe anyone's copyright
or other rights, and that it is lawful. You are responsible for the content you add and for
how you use it.</p>

<h2>What the results mean</h2>
<p>Gesture recognition comes from a statistical model trained on your samples. It can be
wrong, and its confidence score is an estimate, not a guarantee. A Ball Knowledge rating is a
label that you assign to a gesture. It is not measured or discovered by the model. Do not rely
on the service for any decision that matters.</p>

<h2>No warranty</h2>
<p>The service is provided as it is and as available, without warranties of any kind, to the
fullest extent the law allows. It may contain errors and may change or stop working at any time.</p>

<h2>Limit of liability</h2>
<p>To the fullest extent the law allows, {operator} is not liable for any indirect or
consequential loss, or for loss of data, arising from your use of the service. Nothing in these
terms limits liability that cannot be limited by law.</p>

<h2>Acceptable use</h2>
<p>Do not use the service to break the law, to harass anyone, to attempt to gain unauthorised
access to it, or to interfere with its operation.</p>

<h2>Changes to these terms</h2>
<p>These terms may be updated. The date above shows when they last changed. Continued use after
a change means you accept the updated terms.</p>

{governing}

<h2>Contact</h2>
<p>{contact}</p>

</div>
""",
    unsafe_allow_html=True,
)
