from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
import threading

from fastapi import FastAPI, HTTPException
import firebase_admin
from firebase_admin import credentials, firestore
import asyncio
import datetime as datetime



from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Initialize Firebase Admin SDK (only once)
cred = credentials.Certificate('calvinschedulo-de056-firebase-adminsdk-fbsvc-d3f51cef79.json')  # Make sure the path is correct
firebase_admin.initialize_app(cred)

# Firestore instance
db = firestore.client()

app = FastAPI()

class User(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, or you can specify the allowed domains
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.get("/get_user/{username}")
async def get_user(username: str):
    try:
        # Use asyncio to run the Firestore operation in a separate thread
        user_ref = db.collection("user").document(username.lower())
        doc = await asyncio.to_thread(user_ref.get)

        if doc.exists:
            return {"username": doc.id, "data": doc.to_dict()}
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.post("/login")
async def login(request: LoginRequest):
    try:
        user_ref = db.collection("user").document(request.username.lower())
        doc = await asyncio.to_thread(user_ref.get)

        if doc.exists:
            # Compare the passwords (this should be done securely in production)
            if doc.to_dict().get("password") == request.password:
                return {"message": "Login successful"}
            else:
                raise HTTPException(status_code=401, detail="Incorrect password")
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

import requests
import threading

class CanvasRequest(BaseModel):
    api_key: str  # API Key for authentication
    canvas_url: str  # Base URL of the Canvas instance

class SignupRequest(BaseModel):
    username: str
    password: str

# Pydantic model for the request body
class UpdateCanvasRequest(BaseModel):
    username: str
    canvas_key: str
    infrastructure: str

# Function to update canvas details in Firestore
def update_canvas(username: str, canvas_key: str, infrastructure: str):
    # Reference to 'users' collection
    users_ref = db.collection('user')

    # Check if the user exists in the collection
    user_doc = users_ref.document(username).get()

    if not user_doc.exists:
        raise HTTPException(status_code=404, detail=f"User with username '{username}' does not exist.")

    # Prepare the data to be updated
    updates = {
        'canvas_key': canvas_key,
        'infrastructure': infrastructure
    }

    try:
        # Update the user's document with the new values
        users_ref.document(username).update(updates)
        return {"message": f"User {username}'s canvas_key and infrastructure updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {e}")

# FastAPI endpoint to handle the update canvas request
@app.post("/update-canvas")
async def update_canvas_endpoint(request: UpdateCanvasRequest):
    # Call the function to update the user's details
    return update_canvas(request.username, request.canvas_key, request.infrastructure)


@app.post("/creation")
async def signup(request: SignupRequest):
    print("Signup started and locked and loaded")

    username = request.username.lower()  # Ensure case insensitivity
    password = request.password

    # Reference to Firestore user document
    user_ref = db.collection("user").document(username)
    
    # Create user without checking existence (overwrite if exists)
    user_data = {
        "password": password,
        "canvas_key": None,
        "gmail": None,
        "infrastructure": None
                }
    await asyncio.to_thread(user_ref.set, user_data)

    return {"message": "Signup successful. Redirecting to home.", "username": username}

def get_courses(api_key, canvas_url):
    """Fetch all active courses."""
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{canvas_url}/api/v1/courses?enrollment_state=active&state=available"
    all_courses = []

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        courses = response.json()

        if not courses:
            print("No courses found!")  # DEBUG
            return []

        all_courses.extend(courses)
        url = response.links.get("next", {}).get("url")  # Handle pagination

    print(f"Fetched {len(all_courses)} courses.")  # DEBUG
    return all_courses

def fetch_all_assignments(course_id, headers, canvas_url):
    """Fetch all assignments for a course."""
    url = f"{canvas_url}/api/v1/courses/{course_id}/assignments"
    all_assignments = []

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        assignments = response.json()

        if not assignments:
            print(f"No assignments found for course {course_id}!")  # DEBUG
            return []

        all_assignments.extend(assignments)
        url = response.links.get("next", {}).get("url")  # Handle pagination

    print(f"Fetched {len(all_assignments)} assignments for course {course_id}.")  # DEBUG
    return all_assignments

def get_submission_status(course_id, assignment_id, headers, canvas_url):
    """Check if an assignment is submitted."""
    submission_url = f"{canvas_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self"
    response = requests.get(submission_url, headers=headers)

    if response.status_code == 200:
        submission_data = response.json()
        submitted = submission_data.get("submitted_at") is not None
        score = submission_data.get("score", "Not graded")
    else:
        print(f"Failed to fetch submission for assignment {assignment_id} in course {course_id}")  # DEBUG
        submitted = False
        score = "Unknown"

    return submitted, score

def get_unsubmitted_assignments(course_id, api_key, canvas_url):
    """Fetch unsubmitted assignments for a course."""
    headers = {"Authorization": f"Bearer {api_key}"}
    assignments = fetch_all_assignments(course_id, headers, canvas_url)
    if not assignments:
        return []

    course_assignments = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_assignment = {
            executor.submit(get_submission_status, course_id, assignment["id"], headers, canvas_url): assignment
            for assignment in assignments
        }

        for future in future_to_assignment:
            assignment = future_to_assignment[future]
            submitted, score = future.result()

            if not submitted:  # Only include unsubmitted assignments
                course_assignments.append({
                    "name": assignment["name"],
                    "due": assignment.get("due_at", "No due date"),
                    "points": assignment.get("points_possible", "N/A"),
                    "submitted": "No",
                    "score": "N/A"
                })

    print(f"Found {len(course_assignments)} unsubmitted assignments for course {course_id}.")  # DEBUG
    return course_assignments

@app.post("/get_assignments")
def fetch_all_unsubmitted_assignments(request: CanvasRequest):
    """Fetch all unsubmitted assignments for all courses."""
    try:
        courses = get_courses(request.api_key, request.canvas_url)
        if not courses:
            return {"error": "No courses found."}

        assignments_results = {}

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(get_unsubmitted_assignments, course["id"], request.api_key, request.canvas_url): course["name"]
                for course in courses
            }

            for future in futures:
                course_name = futures[future]
                assignments_results[course_name] = future.result()

        return {"courses": assignments_results}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Canvas: {str(e)}")
    
class UsernameRequest(BaseModel):
    username: str

def get_user_info(username):
    """Fetch the canvas key and canvas url from Firebase based on username."""
    user_ref = db.collection('users').document(username)
    user_doc = user_ref.get()
    print("user doc exist?")
    if user_doc.exists:
        user_data = user_doc.to_dict()
        canvas_key = user_data.get('canvas_key')
        canvas_url = user_data.get('infrastructure')
        return canvas_key, canvas_url
    else:
        print(f"User '{username}' not found in Firebase!")
        return None, None

def get_courses(api_key, canvas_url):
    """Fetch all active courses."""
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{canvas_url}/api/v1/courses?enrollment_state=active&state=available"
    all_courses = []

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        courses = response.json()

        if not courses:
            print("No courses found!")
            return []

        all_courses.extend(courses)
        url = response.links.get("next", {}).get("url")  # Handle pagination

    print(f"Fetched {len(all_courses)} courses.")
    return all_courses

def fetch_all_assignments(course_id, headers, canvas_url):
    """Fetch all assignments for a course."""
    url = f"{canvas_url}/api/v1/courses/{course_id}/assignments"
    all_assignments = []

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        assignments = response.json()

        if not assignments:
            print(f"No assignments found for course {course_id}!")
            return []

        all_assignments.extend(assignments)
        url = response.links.get("next", {}).get("url")  # Handle pagination

    print(f"Fetched {len(all_assignments)} assignments for course {course_id}.")
    return all_assignments

def get_submission_status(course_id, assignment_id, headers, canvas_url):
    """Check if an assignment is submitted."""
    submission_url = f"{canvas_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self"
    response = requests.get(submission_url, headers=headers)

    if response.status_code == 200:
        submission_data = response.json()
        submitted = submission_data.get("submitted_at") is not None
        score = submission_data.get("score", "Not graded")
    else:
        print(f"Failed to fetch submission for assignment {assignment_id} in course {course_id}")
        submitted = False
        score = "Unknown"

    return submitted, score

def get_unsubmitted_assignments(course_id, api_key, canvas_url):
    """Fetch unsubmitted assignments for a course."""
    headers = {"Authorization": f"Bearer {api_key}"}
    assignments = fetch_all_assignments(course_id, headers, canvas_url)
    if not assignments:
        return []

    course_assignments = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_assignment = {
            executor.submit(get_submission_status, course_id, assignment["id"], headers, canvas_url): assignment
            for assignment in assignments
        }

        for future in future_to_assignment:
            assignment = future_to_assignment[future]
            submitted, score = future.result()

            if not submitted:  # Only include unsubmitted assignments
                course_assignments.append({
                    "name": assignment["name"],
                    "due": assignment.get("due_at", "No due date"),
                    "points": assignment.get("points_possible", "N/A"),
                    "submitted": "No",
                    "score": "N/A"
                })

    print(f"Found {len(course_assignments)} unsubmitted assignments for course {course_id}.")
    return course_assignments


@app.post("/get_courses")
def get_all_courses_and_assignments(username):
    """Main function to get all courses and their unsubmitted assignments for a user."""
    # Fetch canvas key and url from Firebase using username
    canvas_key, canvas_url = get_user_info(username)
    
    print("hello your doin gweell")

    if not canvas_key or not canvas_url:
        print("Unable to fetch user details.")
        return

    # Fetch the courses
    courses = get_courses(canvas_key, canvas_url)
    if not courses:
        return

    # For each course, fetch unsubmitted assignments
    all_course_assignments = {}
    for course in courses:
        course_id = course["id"]
        print(f"Fetching unsubmitted assignments for course: {course['name']}...")
        unsubmitted_assignments = get_unsubmitted_assignments(course_id, canvas_key, canvas_url)
        all_course_assignments[course["name"]] = unsubmitted_assignments

    return all_course_assignments

# Example usage:
username = "student_username"  # Replace with actual username input
all_courses_and_assignments = get_all_courses_and_assignments(username)

# Display results
if all_courses_and_assignments:
    for course_name, assignments in all_courses_and_assignments.items():
        print(f"Course: {course_name}")
        for assignment in assignments:
            print(f"  - {assignment['name']} (Due: {assignment['due']})")
else:
    print("No courses or assignments found.")
