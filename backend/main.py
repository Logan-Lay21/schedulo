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