from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()
import os
import bcrypt
import traceback
import uuid
from datetime import datetime
import asyncio  # Import asyncio
import random

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize Realtime client (moved inside chat route)

DEFAULT_POSTER_URLS = [
    "hackthonplaceholder.jpeg",
    "hackthonplaceholder1.jpeg",
]

@app.route('/')
def index():
    try:
        # Fetch all events from Supabase
        events_response = supabase.table('events').select('*').execute()
        events = events_response.data if events_response.data else []

        # Assign default poster URLs if poster_url is missing
        for event in events:
            if not event.get('poster_url'):
                event['poster_url'] = url_for('static', filename=random.choice(DEFAULT_POSTER_URLS))

    except Exception as e:
        print(f"Error fetching events: {e}")
        traceback.print_exc()
        events = []

    # Check if user is logged in and pass user_id and role to the template
    user_id = session.get('user_id')
    user_role = session.get('role')  # Get the user's role from the session
    return render_template('index.html', events=events, user_id=user_id, user_role=user_role)

@app.route('/register_event/<event_id>')
def register_event(event_id):
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    user_id = session['user_id']
    return render_template('registration.html', event_id=event_id)

@app.route('/submit_registration', methods=['POST'])
def submit_registration():
    event_id = request.form.get('event_id')
    team_name = request.form.get('team_name')
    leader_name = request.form.get('leader_name')
    leader_email = request.form.get('leader_email')
    leader_college = request.form.get('leader_college')
    leader_course = request.form.get('leader_course')
    leader_year = request.form.get('leader_year')
    leader_mobile = request.form.get('leader_mobile')
    leader_gender = request.form.get('leader_gender')

    member_count = request.form.get('memberCount')  # Access memberCount from the request

    try:
        registration_data = {
            'event_id': event_id,
            'team_name': team_name,
            'leader_name': leader_name,
            'leader_email': leader_email,
            'leader_college': leader_college,
            'leader_course': leader_course,
            'leader_year': leader_year,
            'leader_mobile': leader_mobile,
            'leader_gender': leader_gender
        }

        response = supabase.table('registrations').insert(registration_data).execute()

        if response.data:
            registration_id = response.data[0]['id']  # Get the registration ID

            # Handle team members
            member_count = int(member_count or 0)  # Convert to integer, default to 0 if None
            for i in range(1, member_count + 1):
                member_name = request.form.get(f'member_{i}_name')
                member_email = request.form.get(f'member_{i}_email')
                member_college = request.form.get(f'member_{i}_college')
                member_course = request.form.get(f'member_{i}_course')
                member_year = request.form.get(f'member_{i}_year')
                member_mobile = request.form.get(f'member_{i}_mobile')
                member_gender = request.form.get(f'member_{i}_gender')

                team_member_data = {
                    'registration_id': registration_id,
                    'member_name': member_name,
                    'member_email': member_email,
                    'member_college': member_college,
                    'member_course': member_course,
                    'member_year': member_year,
                    'member_mobile': member_mobile,
                    'member_gender': member_gender
                }

                supabase.table('team_members').insert(team_member_data).execute()

            return redirect(url_for('index'))  # Redirect to the home page
        else:
            return jsonify({'error': f'Failed to submit registration: {response}'}), 500

    except Exception as e:
        print(f"Error submitting registration: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    user_id = session['user_id']

    try:
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        user = response.data[0] if response.data else None

        if not user:
            return "User not found", 404

        if request.method == 'POST':
            age = request.form.get('age')
            mobile = request.form.get('mobile')
            profile_photo = request.files.get('profile_photo')

            profile_photo_url = None
            if profile_photo:
                try:
                    # Generate a unique filename
                    filename = f"{uuid.uuid4()}_{profile_photo.filename}"
                    # Upload the file to Supabase storage
                    response = supabase.storage().from_('profile-photos').upload(
                        path=filename,
                        file=profile_photo.read(),
                        file_options={"content-type": profile_photo.content_type}
                    )

                    if response.status_code == 200:
                        profile_photo_url = f"{SUPABASE_URL}/storage/v1/object/public/profile-photos/{filename}"
                        print(f"Profile photo URL: {profile_photo_url}")
                    else:
                        print(f"Error uploading profile photo: {response.status_code} - {response.text}")

                except Exception as e:
                    print(f"Error uploading profile photo: {e}")
                    traceback.print_exc()
                    return jsonify({'error': str(e)}), 500

            try:
                update_data = {}
                if age:
                    update_data['age'] = age
                if mobile:
                    update_data['mobile'] = mobile
                if profile_photo_url:
                    update_data['profile_photo_url'] = profile_photo_url

                if update_data:
                    response = supabase.table('users').update(update_data).eq('id', user_id).execute()
                    print(f"Database Update Response: {response}")

                    if response.data:
                        print("Profile updated successfully.")
                    else:
                        print(f"Error updating profile: {response}")

            except Exception as e:
                print(f"Error updating profile data: {e}")
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500

            return redirect(url_for('profile'))

    except Exception as e:
        print(f"Error fetching user data: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

    return render_template('profile.html', user=user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            # Insert user data into Supabase
            user_data = {
                'username': username,
                'email': email,
                'password': hashed_password.decode('utf-8'),
                'role': role
            }
            response = supabase.table('users').insert(user_data).execute()

            if response.data:
                user = response.data[0]
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']  # Store the user's role in the session
                return redirect(url_for('signin'))
            else:
                return render_template('signup.html', error='Failed to sign up. Please try again.')
        except Exception as e:
            print(f"Error signing up: {e}")
            traceback.print_exc()
            return render_template('signup.html', error='An error occurred. Please try again.')

    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # Fetch user by email
            response = supabase.table('users').select('*').eq('email', email).execute()
            user = response.data[0] if response.data else None

            if user:
                # Verify password
                if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user['role']  # Store the user's role in the session
                    return redirect(url_for('index'))
                else:
                    return render_template('signin.html', error='Invalid credentials')
            else:
                return render_template('signin.html', error='Invalid credentials')
        except Exception as e:
            print(f"Error signing in: {e}")
            traceback.print_exc()
            return render_template('signin.html', error='An error occurred')

    return render_template('signin.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

@app.route('/organising')
def organising():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    user_id = session['user_id']

    try:
        # Fetch user data from Supabase
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        user = response.data[0] if response.data else None

        if user:
            return render_template('organising.html', user=user)
        else:
            return "User not found", 404

    except Exception as e:
        print(f"Error fetching user data: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/create_event', methods=['POST'])
def create_event():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    organizer_id = session['user_id']
    event_name = request.form.get('event_name')
    event_date = request.form.get('event_date')
    venue = request.form.get('venue')
    description = request.form.get('description')
    poster_url = request.form.get('poster_url')

    try:
        event_data = {
            'organizer_id': organizer_id,
            'event_name': event_name,
            'event_date': event_date,
            'venue': venue,
            'description': description,
            'poster_url': poster_url
        }

        response = supabase.table('events').insert(event_data).execute()

        if response.data:
            return jsonify({'message': 'Event created successfully'}), 200
        else:
            return jsonify({'error': f'Failed to create event: {response}'}), 500
    except Exception as e:
        print(f"Error creating event: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/delete_event/<event_id>', methods=['POST'])
def delete_event(event_id):
    if session.get('role') != 'organizer':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        response = supabase.table('events').delete().eq('id', event_id).execute()
        if response.data:
            return jsonify({'message': 'Event deleted successfully'}), 200
        else:
            return jsonify({'error': f'Failed to delete event: {response}'}), 500
    except Exception as e:
        print(f"Error deleting event: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/my_events')
def my_events():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    user_id = session['user_id']
    user_name = session.get('username')

    try:
        # Fetch registrations for the current user based on the leader_name
        registrations_response = supabase.table('registrations').select('*').eq('leader_name', user_name).execute()
        registrations = registrations_response.data if registrations_response.data else []

        print(f"Registrations: {registrations}")  # Debugging

        # Extract event IDs from registrations
        event_ids = [registration['event_id'] for registration in registrations]

        print(f"Event IDs: {event_ids}")  # Debugging

        events = []
        if event_ids:
            # Fetch events based on the extracted event IDs
            events_response = supabase.table('events').select('*').in_('id', event_ids).execute()
            events = events_response.data if events_response.data else []

            print(f"Events: {events}")  # Debugging

            # Check for existing submissions
            for registration in registrations:
                submission_response = supabase.table('submissions').select('*').eq('event_id', registration['event_id']).execute()
                submissions = submission_response.data if submission_response.data else []
                registration['submission_exists'] = len(submissions) > 0

        else:
            print("No event IDs found.")  # Debugging

    except Exception as e:
        print(f"Error fetching events: {e}")
        traceback.print_exc()
        events = []

    return render_template('my_events.html', events=events, registrations=registrations)

@app.route('/submit_project/<event_id>')
def submit_project(event_id):
    # Handle project submission logic here
    # You can render a form for the user to submit their project
    # Or you can directly process the submission if you have the project data
    return f"<h1>Submit Project for Event ID: {event_id}</h1>"

@app.route('/show_submission_form/<event_id>')
def show_submission_form(event_id):
    return render_template('submission.html', event_id=event_id)

@app.route('/handle_submission', methods=['POST'])
def handle_submission():
    print(request.form)  # Print the form data

    event_id = request.form.get('event_id')
    project_title = request.form.get('project_title')
    project_description = request.form.get('project_description')
    github_link = request.form.get('github_link')
    demo_link = request.form.get('demo_link')
    tech_stack = request.form.get('tech_stack')

    try:
        submission_data = {
            'event_id': event_id,
            'project_title': project_title,
            'project_description': project_description,
            'github_link': github_link,
            'demo_link': demo_link,
            'tech_stack': tech_stack
        }

        print(submission_data)  # Print the submission data

        response = supabase.table('submissions').insert(submission_data).execute()

        print(response)  # Print the Supabase response

        if response.data:
            return redirect(url_for('my_events'))
        else:
            return jsonify({'error': f'Failed to submit project: {response}'}), 500

    except Exception as e:
        print(f"Error submitting project: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/organiser_dashboard')
def organiser_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    organizer_id = session['user_id']

    try:
        # Fetch events created by the organizer
        events_response = supabase.table('events').select('*').eq('organizer_id', organizer_id).execute()
        events = events_response.data if events_response.data else []

        # Extract event IDs
        event_ids = [event['id'] for event in events]

        # Fetch registrations for the organizer's events
        registrations_response = supabase.table('registrations').select('*').in_('event_id', event_ids).execute()
        registrations = registrations_response.data if registrations_response.data else []

        # Fetch all submissions
        submissions_response = supabase.table('submissions').select('*').execute()
        submissions = submissions_response.data if submissions_response.data else []

        # Prepare data for the template
        for registration in registrations:
            # Fetch team members for the registration
            team_members_response = supabase.table('team_members').select('*').eq('registration_id', registration['id']).execute()
            registration['team_members'] = team_members_response.data if team_members_response.data else []

            # Find the submission for this registration, if any
            registration['submission'] = next((sub for sub in submissions if sub['event_id'] == registration['event_id']), None)

        return render_template('organiser submitted dashboard.html', registrations=registrations)

    except Exception as e:
        print(f"Error fetching data for organiser dashboard: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/judges_dashboard')
def judges_dashboard():
    if 'user_id' not in session or session.get('role') != 'judge':
        return redirect(url_for('index'))  # Redirect if not a judge

    user_id = session['user_id']

    try:
        # Fetch user data from Supabase
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        user = response.data[0] if response.data else None

        # Fetch all submissions
        submissions_response = supabase.table('submissions').select('*').execute()
        submissions = submissions_response.data if submissions_response.data else []

        # Fetch all events
        events_response = supabase.table('events').select('*').execute()
        events = events_response.data if events_response.data else []

        # Fetch all registrations
        registrations_response = supabase.table('registrations').select('*').execute()
        registrations = registrations_response.data if submissions_response.data else []

        if user:
            return render_template('judges_dashboard.html', user=user, submissions=submissions, events=events, registrations=registrations)
        else:
            return "User not found", 404

    except Exception as e:
        print(f"Error fetching user data: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/submit_score', methods=['POST'])
def submit_score():
    if 'user_id' not in session or session.get('role') != 'judge':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        submission_id = request.form.get('submission_id')
        event_id = request.form.get('event_id')
        innovation_score = int(request.form.get('innovation_score'))
        functionality_score = int(request.form.get('functionality_score'))
        design_score = int(request.form.get('design_score'))
        impact_score = int(request.form.get('impact_score'))

        # Create a dictionary to store the scores
        scores_data = {
            'submission_id': submission_id,
            'event_id': event_id,
            'innovation_score': innovation_score,
            'functionality_score': functionality_score,
            'design_score': design_score,
            'impact_score': impact_score,
        }

        # Insert the scores into the 'scores' table in Supabase
        response = supabase.table('scores').insert(scores_data).execute()

        if response.data:
            return jsonify({'message': 'Scores submitted successfully'}), 200
        else:
            return jsonify({'error': f'Failed to submit scores: {response}'}), 500

    except Exception as e:
        print(f"Error submitting scores: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/leaderboard')
def leaderboard():
    try:
        # Fetch all scores from Supabase
        scores_response = supabase.table('scores').select('*').execute()
        scores = scores_response.data if scores_response.data else []

        # Fetch all registrations to map event_id to team_name and other details
        registrations_response = supabase.table('registrations').select('*').execute()
        registrations = registrations_response.data if registrations_response.data else []

        # Calculate total scores for each team
        team_scores = {}
        for score in scores:
            event_id = score['event_id']
            submission_id = score['submission_id']
            team_name = None

            # Find the team name associated with the event_id
            for registration in registrations:
                if registration['event_id'] == event_id:
                    team_name = registration['team_name']
                    break

            if team_name:
                if team_name not in team_scores:
                    team_scores[team_name] = {
                        'team_name': team_name,
                        'total_score': 0,
                        'event_id': event_id  # Store event_id for potential filtering
                    }

                team_scores[team_name]['total_score'] += (
                    score['innovation_score'] +
                    score['functionality_score'] +
                    score['design_score'] +
                    score['impact_score']
                )

        # Convert team_scores dictionary to a list for easier rendering
        leaderboard_data = list(team_scores.values())

        # Sort the leaderboard data by total score in descending order
        leaderboard_data.sort(key=lambda x: x['total_score'], reverse=True)

    except Exception as e:
        print(f"Error fetching leaderboard data: {e}")
        traceback.print_exc()
        leaderboard_data = []

    return render_template('leaderboard.html', teams=leaderboard_data)

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    user_id = session['user_id']
    username = session['username']

    try:
        # Fetch all users from Supabase, excluding the current user
        users_response = supabase.table('users').select('id, username').neq('id', user_id).execute()
        users = users_response.data if users_response.data else []
    except Exception as e:
        print(f"Error fetching users: {e}")
        traceback.print_exc()
        users = []

    # Initialize Realtime client inside the route
    realtime = supabase.realtime

    return render_template('chat.html', username=username, users=users)

@app.route('/get_messages')
def get_messages():
    try:
        messages_response = supabase.table('messages').select('*').order('created_at', desc=False).execute()
        messages = messages_response.data if messages_response.data else []
        return jsonify(messages)
    except Exception as e:
        print(f"Error fetching messages: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    username = session['username']
    message_text = request.form.get('message')
    recipient_id = request.form.get('recipient_id')  # Get the recipient_id from the form

    try:
        message_data = {
            'user_id': user_id,
            'username': username,
            'message': message_text,
            'recipient_id': recipient_id if recipient_id != 'public' else None  # Store recipient_id, or None for public
        }
        response = supabase.table('messages').insert(message_data).execute()

        if response.data:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': f'Failed to send message: {response}'}), 500

    except Exception as e:
        print(f"Error sending message: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/team_options')
def team_options():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    return render_template('team_options.html')

@app.route('/post_recruitment', methods=['GET'])
def post_recruitment():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    username = session.get('username')  # Get the username from the session
    return render_template('post_recruitment.html', username=username)

@app.route('/handle_recruitment', methods=['POST'])
def handle_recruitment():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    team_name = request.form.get('team_name')
    description = request.form.get('description')
    skills = request.form.get('skills')
    members_required = request.form.get('members_required')

    try:
        recruitment_data = {
            'user_id': user_id,
            'team_name': team_name,
            'description': description,
            'skills': skills,
            'members_required': int(members_required) if members_required else 1  # Default to 1 if not provided
        }
        response = supabase.table('user_recruitments').insert(recruitment_data).execute()

        if response.data:
            return redirect(url_for('index'))  # Redirect to a suitable page
        else:
            return jsonify({'error': f'Failed to post recruitment: {response}'}), 500

    except Exception as e:
        print(f"Error posting recruitment: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/apply_to_team', methods=['POST'])
def apply_to_team():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    team_id = request.form.get('team_id')

    try:
        application_data = {
            'user_id': user_id,
            'team_id': team_id
        }
        response = supabase.table('team_applications').insert(application_data).execute()

        if response.data:
            return jsonify({'message': 'Application submitted successfully'}), 200
        else:
            return jsonify({'error': f'Failed to submit application: {response}'}), 500

    except Exception as e:
        print(f"Error submitting application: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/find_team')
def find_team():
    if 'user_id' not in session:
        return redirect(url_for('team_options'))

    try:
        # Fetch teams with open slots from Supabase
        teams_response = supabase.table('teams').select('*').gt('open_slots', 0).execute()
        teams = teams_response.data if teams_response.data else []

        # Fetch user recruitments
        recruitments_response = supabase.table('user_recruitments').select('*').execute()
        recruitments = recruitments_response.data if recruitments_response.data else []

        print("Teams Response:", teams_response)  # Print the entire response
        print("Teams Data:", teams)  # Print the teams data
        print("Recruitments Response:", recruitments_response)  # Print the entire response
        print("Recruitments Data:", recruitments)  # Print the recruitments data

    except Exception as e:
        print(f"Error fetching teams: {e}")
        traceback.print_exc()
        teams = []
        recruitments = []

    return render_template('find_team.html', teams=teams, recruitments=recruitments)

if __name__ == '__main__':
    app.run(debug=True)
