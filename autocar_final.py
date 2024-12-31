from mediapipe.tasks import python
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
import cv2
import face_recognition
import time
import requests

# Input filename for image file of the owner's face.
owner_images = [
    "youngjin.jpg",
]

known_face_encodings = []
for img in owner_images:
    loaded_img = face_recognition.load_image_file(img)
    encoded_img = face_recognition.face_encodings(loaded_img)[0]
    known_face_encodings.append(encoded_img)

# Input owner names.
known_face_names = [
    "Kwon Youngjin",
]

face_locations = []
face_encodings = []
authorized = False  # Global variable to track authorization status

# Timer and state for welcome message
recognized_start_time = None
recognized_name = None
recognition_threshold = 5  # seconds

BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
GestureRecognizerResult = mp.tasks.vision.GestureRecognizerResult
VisionRunningMode = mp.tasks.vision.RunningMode

mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
mp_drawing_styles = mp.solutions.drawing_styles

global_result = None

# Server URLs to connect 
url_prefix = 'http://192.168.0.122:8064/'
url3 = url_prefix + 'forward'
url4 = url_prefix + 'backward'
url5 = url_prefix + 'all/1'
url6 = url_prefix + 'all/0'
url7 = url_prefix + 'trunk/1'
url8 = url_prefix + 'trunk/0'
url9 = url_prefix + 'sound/1'
url10 = url_prefix + 'sound/0'
url11 = url_prefix + 'open_close_door'


def print_result(result: GestureRecognizerResult, output_image: mp.Image, timestamp_ms: int):
    global global_result
    global_result = result


options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path='./car_control.task'),
    running_mode=VisionRunningMode.LIVE_STREAM,
    num_hands=1,
    result_callback=print_result)


##############################################
# Part 1. Face Recognition (Owner Authorization)
##############################################

# Get a reference to webcam #0 (the default one)
cap = cv2.VideoCapture(0)

while True:
    # Grab a single frame of video
    success, img = cap.read()

    # Resize frame of video to 1/4 size for faster face recognition processing
    small_img = cv2.resize(img, (0, 0), fx=0.25, fy=0.25)

    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    rgb_small_img = small_img[:, :, ::-1]

    # Find all the faces and face encodings in the current frame of video
    face_locations = face_recognition.face_locations(rgb_small_img)
    face_encodings = face_recognition.face_encodings(rgb_small_img, face_locations)
    face_landmarks_list = face_recognition.face_landmarks(rgb_small_img)

    if face_encodings:
        # Consider only the first face
        face_encoding = face_encodings[0]

        # See if the face is a match for the known face(s)
        name = "Unknown"
        confidence = 0.0
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)

        if True in matches:
            best_match_index = min(range(len(face_distances)), key=face_distances.__getitem__)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
                confidence = 1 - face_distances[best_match_index]  # Convert distance to confidence

        # Check if confidence is above 60%
        if confidence >= 0.6:
            if recognized_name == name:
                # If the same face has been recognized, update the timer
                if time.time() - recognized_start_time >= recognition_threshold:
                    label = f"Welcome, {name}!"
                    cv2.rectangle(img, (0, 0), (400, 50), (0, 0, 0), cv2.FILLED)
                    cv2.putText(img, label, (10, 35), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 1)
                    cv2.imshow('Video', img)
                    cv2.waitKey(1500)  # Show the welcome message for 1.5 seconds

                    # After showing the message, close the window and authorize
                    authorized = True
                    break
                else:
                    label = f"{name}: {confidence * 100:.2f}%"
            else:
                # Reset timer and name if a different face is recognized
                recognized_name = name
                recognized_start_time = time.time()
                label = f"{name}: {confidence * 100:.2f}%"
        else:
            recognized_name = None
            recognized_start_time = None
            label = "No face detected"
    else:
        recognized_name = None
        recognized_start_time = None
        label = "No face detected"

    # Draw landmarks for the first detected face
    if face_landmarks_list:
        face_landmarks = face_landmarks_list[0]
        for feature, points in face_landmarks.items():
            for point in points:
                # Scale back up points since the image was scaled down
                x, y = point[0] * 4, point[1] * 4
                cv2.circle(img, (x, y), 2, (0, 255, 0), -1)

    # Draw the label on the top left corner of the screen
    cv2.rectangle(img, (0, 0), (400, 50), (0, 0, 0), cv2.FILLED)
    font = cv2.FONT_HERSHEY_DUPLEX
    cv2.putText(img, label, (10, 35), font, 1.0, (255, 255, 255), 1)

    # Display the resulting image
    cv2.imshow('Video', img)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release handle to the webcam and close the window
cap.release()
cv2.destroyAllWindows()

print(f"Authorized: {authorized}")


##############################################
# Part 2. Gesture Recognition (Making Commands)
##############################################

if authorized:
    cap = cv2.VideoCapture(0)

    with GestureRecognizer.create_from_options(options) as recognizer:
        while cap.isOpened():
            success, img = cap.read()
            if not success:
                continue
            timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)

            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)

            recognizer.recognize_async(image, int(timestamp))

            if global_result is not None:
                if global_result.hand_landmarks:
                    print(global_result)

                    for idx, hand_landmarks in enumerate(global_result.hand_landmarks):
                        hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
                        hand_landmarks_proto.landmark.extend([
                            landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in
                            hand_landmarks
                        ])

                        mp_drawing.draw_landmarks(
                            img,
                            hand_landmarks_proto,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style())

                        command = global_result.gestures[idx][0].category_name

                        cv2.putText(img, text=command,
                                    org=(
                                        int(hand_landmarks[4].x * img.shape[1]),
                                        int(hand_landmarks[4].y * img.shape[0] + 20)),
                                    fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                                    fontScale=1, color=(255, 0, 0), thickness=2)

                        if command == 'move_forward':
                            requests.get(url3)
                        elif command == 'move_backward':
                            requests.get(url4)
                        elif command == 'light_on':
                            requests.get(url5)
                        elif command == 'light_off':
                            requests.get(url6)
                        elif command == 'trunk_open':
                            requests.get(url7)
                        elif command == 'trunk_close':
                            requests.get(url8)
                        elif command == 'horn_1':
                            requests.get(url9)
                        elif command == 'horn_2':
                            requests.get(url10)
                        elif command == 'door_open_close':
                            requests.get(url11)

            cv2.imshow('image', img)

            if cv2.waitKey(1) == ord('q'):
                break

        cap.release()
