import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def create_event(
    service,
    summary="Untitled Event",
    location="",
    description="",
    start_datetime="2025-03-04T12:00:00-07:00",  # Default start time is 12:00 PM
    end_datetime="2025-03-04T13:00:00-07:00",  # Default end time is 1:00 PM
    attendees=[],  # Be sure to pass in a list
    use_default_reminders=True,  # Sets all reminder settings to default
    method_type="popup",
    method_minutes=30,
    contact_type="email",
    contact_minutes=60,
    colorId=1,  # Sets the color of the item in Google Calender
    recurrence="",  # Pass in the recurrence rule as a string, it will properly be inserted into a list
    classId="",  # Ensure the class ID is accurate
    assignmentName="",  # Assignment as a string
    priority=1,  # Scale 1-10, 1 being extra cred, 10 being a final
    aiGenerated=False,  # Is this item AI generated?
):

    # If no attendees are provided, set a default empty list
    if attendees is None:
        attendees = ["calvinschedulo@gmail.com"]

    # Set reminders overrides based on use_default_reminders
    reminders = {
        "useDefault": use_default_reminders,
    }

    if not use_default_reminders:
        reminders["overrides"] = [
            {
                "method": method_type,
                "minutes": method_minutes
            },
            {
                "method": contact_type,
                "minutes": contact_minutes
            }
        ]

    # Create the event body using the passed arguments
    event = {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {
            "dateTime": start_datetime,
            "timeZone": "America/Los_Angeles",  # Default time zone
        },
        "end": {
            "dateTime": end_datetime,
            "timeZone": "America/Los_Angeles",  # Default time zone
        },
        # List of email addresses
        "attendees": [{"email": email} for email in attendees],
        "reminders": reminders,
        "colorId": colorId,
        "recurrence": [recurrence if recurrence else None],
        "extendedProperties": {
            "private": {
                "classID": classId,
                "assignmentName": assignmentName,
                "priority": priority,
                "aiGenerated": aiGenerated,

            }
        }
    }

    # Insert the event into the Google Calendar
    event = service.events().insert(calendarId="primary", body=event).execute()

    print(f'Event created: {event.get("htmlLink")}')


def delete_event_by_assignment(service, events, course, assignment):
    calendar_id = 'primary'  # The calendar ID you're working with
    event_found = False

    try:
        # Iterate through the events you've already retrieved
        for event in events:
            private = event.get('extendedProperties', {}).get('private', {})

            # Check if the event has the correct classID and assignment_name
            if private.get('classID') == course and private.get('assignmentName') == assignment and private.get('aiGenerated'):
                # Get the event ID and delete the event
                event_id = event['id']
                service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
                print(f"Event with ID {event_id} has been deleted.")
                event_found = True
        if not event_found:
            print(f"No event found with classID {
                  course} and assignmentName {assignment}.")
    except HttpError as error:
        print(f"An error occurred: {error}")


def delete_event_by_name(service, events, name):
    calendar_id = 'primary'  # The calendar ID you're working with
    event_found = False

    try:
        # Iterate through the events you've already retrieved
        for event in events:
            title = event.get('summary')
            private = event.get('extendedProperties', {}).get('private', {})

            # Check if the event has the correct classID and assignment_name
            if title == name and private.get('aiGenerated'):
                # Get the event ID and delete the event
                event_id = event['id']
                service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
                print(f"Event with ID {event_id} has been deleted.")
                event_found = True
        if not event_found:
            print(f"No event found with summary {name}.")
    except HttpError as error:
        print(f"An error occurred: {error}")


def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time

        eight_days_later = (datetime.datetime.utcnow() +
                            datetime.timedelta(days=8)).isoformat() + "Z"
        print("Getting the upcoming events")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                timeMax=eight_days_later,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        for event in events:
            # Get the start and summary for the event
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "No summary available")
            location = event.get("location", "No location provided")
            description = event.get("description", "No description provided")
            end = event["end"].get("dateTime", "No end time provided")

            # Retrieve extended properties (if available) for private information
            private_properties = event.get(
                'extendedProperties', {}).get('private', {})

            # Retrieve attendees (if available)
            attendees = event.get('attendees', [])

            # Get reminder settings (if applicable)
            reminders = event.get('reminders', {}).get('useDefault', False)

            # Access recurrence rule (if available)
            recurrence = event.get('recurrence', "No recurrence rule")

            # Access the classId, assignmentName, priority, and aiGenerated flags
            class_id = private_properties.get('classId', "No class ID")
            assignment_name = private_properties.get(
                'assignmentName', "No assignment name")
            priority = private_properties.get('priority', "No priority set")
            ai_generated = private_properties.get('aiGenerated', False)

            # Now, print all the gathered information
            print(f"Start: {start}")
            print(f"Summary: {summary}")
            print(f"Location: {location}")
            print(f"Description: {description}")
            print(f"End: {end}")
            print(f"Attendees: {attendees}")
            print(f"Reminders (use default): {reminders}")
            print(f"Recurrence: {recurrence}")
            print(f"Class ID: {class_id}")
            print(f"Assignment Name: {assignment_name}")
            print(f"Priority: {priority}")
            print(f"AI Generated: {ai_generated}")
            print("-" * 40)

        service.events().insert

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
