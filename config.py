"""Centralised settings for Ball Knowledge Vision AI.

Everything tunable lives here so the other modules never hardcode paths or
thresholds.
"""
import os
from pathlib import Path

# --- Paths (all relative to the project root so the project stays portable) ---
PROJECT_ROOT = Path(__file__).resolve().parent
# BALLKNOWLEDGE_DATA_DIR lets tests/previews use a scratch folder instead of your real data.
DATA_DIR = Path(os.environ.get("BALLKNOWLEDGE_DATA_DIR") or PROJECT_ROOT / "data")
MODELS_DIR = PROJECT_ROOT / "models"
MEDIAPIPE_MODELS_DIR = MODELS_DIR / "mediapipe"   # downloaded landmark models
# Where the trained classifier and its reports are written. BALLKNOWLEDGE_MODEL_DIR redirects
# them (used by tests and previews) without touching your real trained model.
MODEL_OUTPUT_DIR = Path(os.environ.get("BALLKNOWLEDGE_MODEL_DIR") or MODELS_DIR)
MODEL_PATH = MODEL_OUTPUT_DIR / "gesture_model.joblib"
LABELS_PATH = MODEL_OUTPUT_DIR / "label_mapping.json"
REPORT_PATH = MODEL_OUTPUT_DIR / "training_report.json"
SAMPLES_CSV = DATA_DIR / "samples.csv"            # one row per labelled sample
DATASET_META = DATA_DIR / "dataset_meta.json"     # feature mode/length the samples were made with
MEMES_DIR = PROJECT_ROOT / "assets" / "memes"
# Gesture -> meme title, image, Ball Knowledge rating and description (see dataset_manager.py)
MEMES_FILE = MEMES_DIR / "memes.json"
MEME_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif")
MEME_MAX_UPLOAD_MB = 10       # larger images are refused on the Memes page
# The meme panel refreshes twice a second and sends its image each time, so large images
# are shrunk for display (the file in assets/memes/ is not changed).
MEME_DISPLAY_MAX_PX = 900     # longest side of the shown image
MEME_DISPLAY_MAX_KB = 250     # images already smaller than this (and this size) are sent as they are

# --- Camera ---
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_IDEAL_FPS = 30
# Pipeline latency is the bottleneck, not frame rate: we always process the
# newest frame and drop stale ones (predictor.LiveRecognizer), which keeps the UI responsive.

# --- Landmarks / features ---
# "hands"      -> features from up to two hands
# "hands+pose" -> hands plus upper/full-body pose (for gestures that involve the body)
# Changing this changes the feature length, so retrain after changing it.
FEATURE_MODE = "hands"
MAX_HANDS = 2
DETECTION_CONFIDENCE = 0.6    # MediaPipe: minimum confidence to detect a hand/pose
TRACKING_CONFIDENCE = 0.5
SHOW_LANDMARKS_DEFAULT = True

# --- Data collection ---
COLLECT_RATE_HZ = 10          # samples saved per second while recording (avoids near-duplicate frames)
COLLECT_COUNTDOWN_S = 3       # time to get your hand ready after pressing Record
COLLECT_TARGET_DEFAULT = 100  # samples per recording (3 recordings ~ 300)
COLLECT_TARGET_MAX = 500
TARGET_MIN_PER_CLASS = 100    # below this a class is "too few samples"
TARGET_GOOD_PER_CLASS = 300   # initial collection goal per class
MIN_SESSIONS_PER_CLASS = 3    # separate recordings per gesture, so a test split can hold one out

# --- Training ---
# The model is softmax regression trained by gradient descent (gd_model.py). Each recording
# is tested by a model trained on all the other recordings, so a gesture needs 2 recordings
# to be tested at all; 3 or more (MIN_SESSIONS_PER_CLASS) give steadier numbers.
MIN_SESSIONS_FOR_TRAINING = 2
# Regularisation strengths tried. Training keeps the one with the lowest cost on held-out
# recordings. Larger values give smoother, less confident models. 0.003 was added on
# 17 October together with augmentation (below), which keeps it from being confident on
# recordings it has not seen: no held-out frame wrong at 90% confidence or more, and no wrong
# meme in the clip replay. 0.001 had a lower held-out cost but 1 to 2 frames wrong at 90% or
# more and a wrong meme for 3 frames in one replayed clip, so the list stops at 0.003.
GD_L2_OPTIONS = (1.0, 0.3, 0.1, 0.03, 0.01, 0.003)
GD_MAX_STEPS = 20000          # gradient descent stops here if it has not reached the minimum
GD_TOLERANCE = 1e-6           # the minimum is reached when the gradient is smaller than this
# Landmark augmentation, at training time only (in every held-out test as well as the final
# model): each training sample also gets this many copies with each hand turned up to
# GD_AUGMENT_ROTATION_DEG degrees about its wrist and every point moved by noise of
# GD_AUGMENT_NOISE hand sizes. Nothing is saved. 0 copies turns it off. The fixed seed keeps
# training deterministic.
GD_AUGMENT_COPIES = 4
GD_AUGMENT_ROTATION_DEG = 15.0
GD_AUGMENT_NOISE = 0.01
GD_AUGMENT_SEED = 0
NONE_LABEL = "none"           # gesture id for "a hand, but no gesture"; it has no meme
CONFIDENCE_THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9)   # shown in the report to help choose a cutoff

# --- Recognition (used from Stage 5 onwards) ---
# A prediction below this confidence is shown as "Unrecognised". The confidence is the
# model's own estimate, not a calibrated probability; use the cutoff table on the
# Model performance page to choose a value.
DEFAULT_CONFIDENCE_THRESHOLD = 0.70
TOP_PREDICTIONS = 3           # top scores kept on each Prediction (no page lists them since 17 October)
SMOOTHING_WINDOW = 7          # number of consecutive frames in the voting window
MIN_STABLE_FRAMES = 4         # frames a gesture must win the vote before it shows

# --- Recent detections (Stage 7) ---
# Kept in memory for the current browser session only, never written to disk.
HISTORY_LENGTH = 10           # most recent detections listed on the dashboard
# The same gesture is listed again only after it has not been the result for this long,
# so a hand that drops out for a moment does not add a duplicate entry.
HISTORY_REPEAT_GAP_S = 2.0

# --- Dashboard ---
APP_TITLE = "Ball Knowledge Vision AI"
FAVICON_PATH = PROJECT_ROOT / "assets" / "favicon.png"

# --- Legal pages (shown on the Privacy and Terms pages) ---
# Fill these in before any public launch. While they are empty, those pages show a notice.
OPERATOR_NAME = ""            # person or company responsible for this site
CONTACT_EMAIL = ""            # where people can reach you about privacy or the terms
GOVERNING_LAW = ""            # e.g. "the laws of England and Wales"; the clause is omitted if empty
LEGAL_LAST_UPDATED = "14 October 2026"
FPS_SMOOTHING = 0.9           # exponential moving average factor for the FPS readout
