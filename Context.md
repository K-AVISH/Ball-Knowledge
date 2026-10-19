# Ball Knowledge Vision AI — Project Context  
## 1. Project objective  
Build an AI-powered web dashboard that uses a live webcam feed to recognise custom hand gestures or visual poses and automatically display a corresponding image or meme from a predefined dataset.  
Each recognised gesture must be associated with:  
* A unique gesture label.  
* A matching meme image.  
* A Ball Knowledge rating or level.  
* A short description or explanation.  
* A confidence score indicating how certain the AI is about the recognition.  
The application should operate in real time, feel interactive, have a modern interface, and allow new gestures and memes to be added without rewriting the core application.  
## 2. Recommended technology stack  
Use Python as the primary programming language.  
* **Computer vision:** OpenCV for webcam frame capture and image processing.  
* **Hand landmark detection:** MediaPipe for extracting hand landmarks from the camera feed.  
* **Machine learning:** Scikit-learn to train a custom gesture classification model using extracted landmarks.  
* **Live dashboard:** Streamlit for the user interface and streamlit-webrtc for real-time webcam streaming.  
* **Data handling:** Pandas and CSV or JSON files for the dataset and prediction history.  
* **Model storage:** Joblib for saving and loading the trained classifier.  
* **Image storage:** Local image assets organised by gesture ID.  
Do not train a large deep-learning model from scratch for the first version. Use a pretrained landmark detector and train a separate classifier on your own labelled gesture data.  
## 3. How the application should work  
Implement the following pipeline:  
1. The user opens the web application and grants webcam permission.  
2. The camera captures frames continuously.  
3. The vision component detects the user's hand and extracts its landmark coordinates.  
4. The custom-trained model analyses these features and predicts the gesture class.  
5. A confidence threshold and prediction-stabilisation mechanism determine whether the classification is reliable.  
6. The application searches its dataset for the corresponding gesture ID.  
7. The relevant meme, Ball Knowledge rating, and description appear automatically on the dashboard.  
8. Recent predictions are added to a session history.  
For example, when the user performs a gesture labelled four_gesture, the model should recognise it, retrieve the image linked to that gesture, and display the corresponding Ball Knowledge card.  
This mapping is illustrative. The actual gesture labels, images, and ratings must be configurable.  
If no hand is detected or the prediction is uncertain, display an appropriate message instead of guessing or showing an unrelated meme.  
## 4. AI model and training requirements  
Create a genuine model-training pipeline rather than hardcoding the gesture predictions.  
**Data collection**  
Build a data collection tool that allows the developer to:  
* Select or enter a gesture label.  
* Start collecting examples through the webcam.  
* Capture landmark features and their corresponding labels.  
* Save the collected data into a structured dataset.  
* View the number of samples collected for each gesture.  
Start with approximately 5–10 gesture classes and aim for around 100–300 labelled samples per class as an initial collection target.  
Capture examples under different lighting conditions, hand positions, distances, backgrounds, and orientations. Include examples from multiple people when possible.  
**Feature extraction**  
Use the landmark detector to obtain the hand's key points. Normalise the coordinates so that predictions are less dependent on where the hand appears in the frame and how large it looks.  
Use these extracted features as inputs to the custom classifier.  
**Model training**  
Create a separate train_model.py script that:  
* Loads the collected and labelled data.  
* Validates the dataset and checks for missing or malformed records.  
* Splits the data into training, validation, and test sets without leakage between recordings.  
* Trains a suitable baseline classifier, such as a Random Forest or support-vector machine.  
* Evaluates the model using accuracy, precision, recall, F1-score, and a confusion matrix.  
* Saves the trained model and label mapping.  
* Reports which gestures the model struggles to distinguish.  
Save the trained model locally so that the dashboard does not retrain the model every time it starts.  
The training process must be repeatable when new examples are collected.  
## 5. Dataset and meme matching  
Create a structured image library. Every gesture class must have a corresponding metadata record and at least one valid image.  
A metadata record should contain fields such as:  
* gesture_id  
* gesture_name  
* meme_title  
* image_path  
* ball_knowledge_level  
* description  
* confidence_threshold  
Example record:  
* Gesture ID: four_gesture  
* Gesture name: Four  
* Meme title: Configurable meme title  
* Image path: assets/memes/four_gesture.jpg  
* Ball Knowledge level: Configurable rating  
* Description: A short explanation of the meme  
* Confidence threshold: A configurable value  
Store the actual images in the appropriate folders. Use relative file paths so that the application remains portable.  
Provide a clear way to add a new gesture, upload its meme image, edit its description, and assign its rating.  
The Ball Knowledge rating is metadata associated with the gesture and its meme. It must not be presented as something the vision model independently discovered.  
## 6. Live dashboard design  
Build a modern, dark-themed dashboard with a football and AI aesthetic. Use a clean layout, readable typography, responsive cards, subtle animations, and a clear visual hierarchy.  
**Main screen**  
**A. Live camera panel**  
* Display the live webcam feed.  
* Overlay detected hand landmarks when available.  
* Show whether the camera is connected and a hand has been detected.  
* Provide camera start and stop controls.  
**B. Recognition panel**  
* Show the currently predicted gesture.  
* Display the confidence score as a percentage.  
* Show the top predictions when useful.  
* Display an explicit uncertain or unrecognised state.  
**C. Meme result panel**  
* Automatically display the matching meme image.  
* Show the meme title and gesture label.  
* Show the associated Ball Knowledge rating.  
* Include a short description.  
**D. Live statistics**  
* Number of predictions made during the current session.  
* Number of recognised gesture classes.  
* Current processing FPS or latency.  
* Most recently recognised gesture.  
* Current model status.  
**E. Recent activity**  
* Display a short history of recent detections.  
* Include the gesture label, confidence, and time of detection.  
* Prevent the history from filling with duplicate entries from every video frame.  
**Additional pages**  
Create three optional dashboard pages:  
1. **Dataset Manager:** View gesture classes, add or edit metadata, and upload matching images.  
2. **Model Performance:** Show training metrics, per-class performance, and the confusion matrix.  
3. **Prediction History:** Review the gestures detected during the current session.  
Do not add unnecessary features that make the first version unreliable.  
## 7. Recognition stability and performance  
Frame-by-frame classification may fluctuate when the user moves their hand. Address this with prediction smoothing or a short voting window across consecutive frames.  
Require a gesture to be recognised consistently before updating the main result card. Use a confidence threshold to reject weak predictions.  
The application must:  
* Continue operating when no hand is visible.  
* Handle missing or invalid dataset images gracefully.  
* Avoid retraining during ordinary live recognition.  
* Keep camera processing and dashboard updates responsive.  
* Release the webcam properly when the session stops.  
* Display useful error messages rather than crashing silently.  
Aim for a responsive local prototype, prioritising stable recognition over an unnecessarily high frame rate.  
## 8. Suggested project structure  
Organise the project into separate files and modules:  
* app.py — Streamlit dashboard and page layout.  
* vision.py — Webcam frame processing and landmark extraction.  
* data_collector.py — Capture and label training examples.  
* train_model.py — Train, validate, evaluate, and save the model.  
* predictor.py — Load the model and perform gesture classification.  
* dataset_manager.py — Read and validate gesture metadata.  
* config.py — Centralised application settings.  
* data/ — Training features and labels.  
* models/ — Saved classifier and label mapping.  
* assets/memes/ — Meme images.  
* tests/ — Tests for prediction, metadata, and image mapping.  
* requirements.txt — Python dependencies.  
* README.md — Setup, training, and execution instructions.  
Keep camera processing, ML training, prediction logic, dataset handling, and the user interface separate.  
## 9. Development phases  
**Phase 1 — Functional prototype**  
Build a dashboard that opens the webcam, detects a hand, predicts a gesture using a placeholder or baseline classifier, and displays a corresponding meme from the dataset.  
The interface must already support an unrecognised state.  
**Phase 2 — Custom model**  
Implement the data collection tool, train a classifier on labelled examples, save the model, and integrate it into the live prediction pipeline.  
**Phase 3 — Dataset integration**  
Connect predictions to the metadata and image library. Enable new gesture classes, new meme images, and configurable ratings.  
**Phase 4 — Live dashboard improvements**  
Add prediction smoothing, confidence indicators, recent detection history, processing statistics, and model performance visualisations.  
**Phase 5 — Testing and refinement**  
Test in different lighting conditions, distances, backgrounds, and with different users. Correct common confusions and add training examples for poorly recognised gestures.  
Only consider cloud deployment after the application works reliably on a local machine.  
## 10. Acceptance criteria  
The project is complete when:  
1. The application launches locally and accesses the webcam with permission.  
2. It recognises custom gestures using a trained classifier.  
3. It automatically displays the correct dataset image for a recognised gesture.  
4. The Ball Knowledge rating and description match the dataset metadata.  
5. The application rejects uncertain predictions instead of displaying arbitrary results.  
6. A new gesture can be added by collecting labelled samples, training the model, and adding its metadata and image.  
7. The dashboard updates during live camera use.  
8. Training metrics and a held-out test evaluation are available.  
9. Camera errors, missing images, and missing models are handled gracefully.  
10. The README explains installation, data collection, training, and execution.  
## 11. Instructions for implementation  
Build the project incrementally. Start with the webcam and basic dashboard, then implement data collection, model training, classification, and dataset matching.  
Write complete, runnable code rather than pseudocode. Explain the purpose of each module, provide the exact terminal commands required to install dependencies and run the application, and make the setup suitable for a beginner using Python on macOS.  
Do not fabricate accuracy scores or claim a model is trained when it has only been hardcoded or mocked. Clearly distinguish prototype results from measured test results.  
Prioritise a working, maintainable end-to-end system before adding complex features.  
