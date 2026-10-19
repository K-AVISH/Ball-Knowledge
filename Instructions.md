# BUILD INSTRUCTIONS: AI BALL KNOWLEDGE MEME RECOGNITION DASHBOARD  
Act as a senior AI/ML engineer and full-stack developer. Build a complete, working passion project that uses a live webcam to recognise gestures performed by a user and automatically display matching memes from a custom image dataset.  
Do not just explain the architecture or generate a static UI. Implement the actual application with working computer vision, machine learning, dataset matching, and a live dashboard.  
## 1. TECHNOLOGY STACK  
Use the following technologies:  
* Python as the main programming language.  
* Figma for the web dashboard.  
* OpenCV for webcam access and image processing.  
* MediaPipe for hand and pose landmark detection.  
* Scikit-learn for training a custom gesture classification model.  
* NumPy and Pandas for data processing.  
* Joblib for saving and loading the trained model.  
* JSON or CSV for dataset metadata.  
Keep the application local-first so that it can run on my computer without requiring paid APIs or cloud services.  
## 2. BUILD THE LIVE CAMERA SYSTEM  
Create a live webcam interface that continuously captures frames and analyses the user's visual input.  
Implement the following:  
1. Request camera permission and allow the user to start and stop the camera.  
2. Detect the user's hand and extract its landmark coordinates.  
3. Allow the architecture to support body-pose landmarks if required for gestures involving more than the hands.  
4. Preprocess the extracted features so predictions are less sensitive to the hand's location and size in the frame.  
5. Feed the features into the trained machine learning model.  
6. Display the recognised gesture and prediction confidence in real time.  
7. Display an appropriate message when no gesture is detected or the model is uncertain.  
Do not rely on simple hardcoded image recognition rules. The final recognition system must use a trainable machine learning classifier.  
## 3. IMPLEMENT CUSTOM MODEL TRAINING  
Create a data collection tool that lets me train the AI to recognise the gestures I choose.  
Implement these features:  
* Let me enter a gesture name or select an existing class.  
* Use the webcam to capture labelled examples of that gesture.  
* Extract and save the corresponding hand or pose landmark features.  
* Store the label alongside every training sample.  
* Display the number of samples collected for each gesture.  
* Allow me to collect examples for multiple gesture classes.  
* Train a Scikit-learn classifier using the collected data.  
* Evaluate the model on held-out data and display accuracy, per-class performance, and a confusion matrix.  
* Save the trained model and class-label mapping.  
* Load the saved model automatically when the application starts.  
Use a suitable baseline classifier, such as Random Forest. Add prediction smoothing and a configurable confidence threshold.  
Prevent training and test data from leaking into each other. Where possible, split samples by recording session rather than randomly splitting neighbouring video frames.  
Do not claim that the model has been trained successfully until real training data has been collected and training has completed.  
## 4. BUILD THE MEME DATASET SYSTEM  
Create a dataset manager that connects every recognised gesture to a specific image and its associated Ball Knowledge rating.  
Use this structure for each dataset record:  
* gesture_id  
* gesture_name  
* meme_title  
* image_path  
* ball_knowledge_level  
* description  
Store the actual images in a local folder called assets/memes/.  
Create a metadata file that maps every gesture to its correct image and associated information.  
Allow me to add new gestures, assign images, edit descriptions, and change Ball Knowledge ratings without modifying the core recognition code.  
When the AI recognises a gesture, use the predicted class to retrieve the matching metadata record and display its associated meme.  
For example, if I train the model to recognise a gesture called four_gesture, the application should retrieve the image associated with four_gesture and display its configured Ball Knowledge rating.  
The gesture names, images, ratings, and descriptions must be configurable. Do not create fake recognition results or depend on a fixed set of gestures.  
Validate image paths and handle missing images gracefully.  
## 5. CREATE THE LIVE DASHBOARD  
Design a polished, modern dashboard with a dark theme, football-inspired styling, clean typography, and an AI analytics aesthetic.  
The dashboard must have the following components.  
**A. Live webcam panel**  
* Live video feed.  
* Optional overlay displaying detected landmarks.  
* Camera connection status.  
* Hand or pose detection status.  
* Start and stop controls.  
**B. Current prediction panel**  
* Recognised gesture name.  
* Model confidence percentage.  
* Recognition status.  
* Optional top alternative predictions.  
* Clear indication when the prediction is uncertain.  
**C. Meme display panel**  
* Display the matched meme image prominently.  
* Show the meme title.  
* Show the detected gesture.  
* Show its Ball Knowledge rating or level.  
* Show a short description.  
Update this panel automatically when the recognised gesture changes. Do not require the user to click a button to reveal the matching meme.  
**D. Live statistics**  
Display:  
* Total recognised gestures in the current session.  
* Number of available gesture classes.  
* Current processing speed in FPS, where measurable.  
* Latest recognised gesture.  
* Model loading and training status.  
**E. Recent detections**  
Display a history of recent recognised gestures with their timestamps, labels, and confidence scores.  
Do not add a new history entry for every video frame. Record meaningful changes in the prediction.  
## 6. MAKE THE RECOGNITION RELIABLE  
Implement the following safeguards:  
* Smooth predictions across consecutive frames.  
* Require a gesture to remain stable briefly before changing the main result.  
* Use a configurable confidence threshold.  
* Show an unrecognised state when confidence is insufficient.  
* Avoid displaying random or unrelated memes when a prediction fails.  
* Handle camera disconnection, missing models, invalid metadata, and missing image files.  
* Keep the interface responsive during live processing.  
* Release webcam resources when the user stops the camera.  
Do not display an incorrect high-confidence prediction merely to make the application look functional.  
## 7. ORGANISE THE PROJECT PROPERLY  
Create a maintainable project with these modules:  
app.py — Main Streamlit dashboard.  
vision.py — Webcam capture and landmark extraction.  
data_collector.py — Collect and label gesture training examples.  
train_model.py — Train and evaluate the classifier.  
predictor.py — Load the model and run predictions.  
dataset_manager.py — Manage gesture metadata and meme images.  
config.py — Centralised settings and confidence thresholds.  
data/ — Stored training samples.  
models/ — Saved trained models and label mappings.  
assets/memes/ — User-provided meme images.  
tests/ — Basic application and data validation tests.  
requirements.txt — Required Python packages.  
README.md — Installation, usage, dataset preparation, and training instructions.  
Adapt this structure where technically necessary, but keep the modules separated by responsibility.  
## 8. DEVELOPMENT ORDER  
Build the application in the following order. Complete and test each stage before moving to the next.  
**Stage 1:** Set up the Python project and build the working webcam dashboard.  
**Stage 2:** Integrate MediaPipe landmark detection and show detected landmarks.  
**Stage 3:** Implement the data collection interface and save labelled training examples.  
**Stage 4:** Implement custom model training, evaluation, and model saving.  
**Stage 5:** Integrate the trained classifier into live camera inference.  
**Stage 6:** Build the metadata manager and automatically display the corresponding meme and Ball Knowledge rating.  
**Stage 7:** Add prediction smoothing, confidence indicators, recent history, and dashboard statistics.  
**Stage 8:** Test the complete pipeline and fix errors.  
Do not skip directly to the final UI. Build the recognition pipeline first, then make the interface polished.  
## 9. EXECUTION REQUIREMENTS  
I am a beginner-to-intermediate Python programmer working on a personal passion project. Make the setup easy to follow on macOS.  
Provide:  
* Complete runnable source code.  
* Exact terminal commands for creating the environment and installing dependencies.  
* Exact commands to launch the dashboard.  
* Exact instructions for collecting training samples.  
* Exact instructions for training and evaluating the model.  
* Instructions for adding new gestures and matching images.  
* Clear error messages and useful debugging information.  
Use compatible package versions and avoid unnecessary dependencies.  
Before declaring the project complete, run the available tests and verify that the modules integrate correctly. Do not assume the webcam is available in your execution environment; provide a way to validate the code and explain how I can test camera access locally.  
## 10. FINAL SUCCESS CRITERIA  
The finished application must allow me to:  
1. Open a live webcam dashboard.  
2. Show a gesture to the camera.  
3. Have my trained model identify the gesture.  
4. Automatically display the matching image from my own dataset.  
5. Display the associated Ball Knowledge rating and description.  
6. See confidence scores and recent recognition activity.  
7. Collect new training samples and train the model to recognise additional gestures.  
8. Add new memes and link them to recognised gesture classes.  
9. Run the project locally without paid services.  
Start by creating the actual project files and implementing Stage 1. Continue through the stages in order, maintaining working code as the project grows. If you cannot execute a stage in the current environment, provide the complete implementation and clearly identify what remains to be tested locally.  
