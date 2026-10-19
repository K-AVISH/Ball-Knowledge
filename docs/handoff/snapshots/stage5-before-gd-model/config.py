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

# --- Camera ---
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_IDEAL_FPS = 30
# Pipeline latency is the bottleneck, not frame rate: we always process the
# newest frame and drop stale ones (see app.py), which keeps the UI responsive.

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
TRAIN_SEED = 42
MIN_SESSIONS_FOR_TRAINING = 3     # every gesture needs this many separate recordings
VAL_SESSION_FRACTION = 0.2        # share of each gesture's recordings held out for validation
TEST_SESSION_FRACTION = 0.2       # share held out for the final test (never used to pick a model)
CONFIDENCE_THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9)   # shown in the report to help choose a cutoff

# --- Recognition (used from Stage 5 onwards) ---
# A prediction below this confidence is shown as "Unrecognised". The confidence is the
# model's own estimate, not a calibrated probability; use the cutoff table on the
# Model performance page to choose a value.
DEFAULT_CONFIDENCE_THRESHOLD = 0.70
TOP_PREDICTIONS = 3           # how many gestures the recognition panel lists with their scores
SMOOTHING_WINDOW = 7          # number of consecutive frames in the voting window
MIN_STABLE_FRAMES = 4         # frames a gesture must win the vote before it shows

# --- Dashboard ---
APP_TITLE = "Ball Knowledge Vision AI"
FAVICON_PATH = PROJECT_ROOT / "assets" / "favicon.png"

# --- Legal pages (shown on the Privacy and Terms pages) ---
# Fill these in before any public launch. While they are empty, those pages show a notice.
OPERATOR_NAME = ""            # person or company responsible for this site
CONTACT_EMAIL = ""            # where people can reach you about privacy or the terms
GOVERNING_LAW = ""            # e.g. "the laws of England and Wales"; the clause is omitted if empty
LEGAL_LAST_UPDATED = "13 October 2026"
FPS_SMOOTHING = 0.9           # exponential moving average factor for the FPS readout
