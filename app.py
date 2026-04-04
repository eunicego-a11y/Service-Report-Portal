import os
import json
import base64
import traceback
import requests
import sys
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
USERS_FILE = 'users.json'

if not app.secret_key or app.secret_key == "dev-secret-key-change-in-production":
    print("WARNING: No SECRET_KEY env var set. Using insecure default.")

# --- Monday.com OAuth Setup ---
oauth = OAuth(app)

print(f"[OAUTH] Initializing Monday.com OAuth...")
print(f"[OAUTH] Client ID exists: {bool(os.getenv('MONDAY_OAUTH_CLIENT_ID'))}")
print(f"[OAUTH] Client Secret exists: {bool(os.getenv('MONDAY_OAUTH_CLIENT_SECRET'))}")

try:
    monday = oauth.register(
        name='monday',
        client_id=os.getenv('MONDAY_OAUTH_CLIENT_ID'),
        client_secret=os.getenv('MONDAY_OAUTH_CLIENT_SECRET'),
        authorize_url='https://auth.monday.com/oauth2/authorize',
        access_token_url='https://auth.monday.com/oauth2/token',
        userinfo_endpoint='https://api.monday.com/v2',
        client_kwargs={},
        token_auth_method='client_secret_post'  # Send credentials in POST body
    )
    print(f"[OAUTH] [OK] Monday.com OAuth configured successfully")
except Exception as e:
    print(f"[OAUTH] [ERROR] Error configuring Monday.com OAuth: {str(e)}")
    print(traceback.format_exc())
    monday = None

# --- Authentication Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, name="User"):
        self.id = id
        self.name = name

@login_manager.user_loader
def load_user(user_id):
    users = _read_users()
    user_data = next((user for user in users if user['username'] == user_id), None)
    if user_data:
        return User(user_data['username'], user_data['username'])
    return None

# --- Monday API Config ---
API_KEY = os.getenv("MONDAY_API_KEY")
MAIN_BOARD = os.getenv("MAIN_BOARD_ID")
LINK_BOARD = os.getenv("LINKED_BOARD_ID")
URL = "https://api.monday.com/v2"
FILE_URL = "https://api.monday.com/v2/file"

if not all([API_KEY, MAIN_BOARD, LINK_BOARD]):
    print("ERROR: Missing required env vars: MONDAY_API_KEY, MAIN_BOARD_ID, LINKED_BOARD_ID")

HEADERS = {"Authorization": API_KEY, "API-Version": "2023-10"}

def _read_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def _write_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)


def _monday_graphql(query, variables=None):
    """Execute a Monday.com GraphQL query/mutation via the service API key."""
    payload = {'query': query}
    if variables:
        payload['variables'] = variables
    return requests.post(URL, json=payload, headers=HEADERS).json()


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('signup'))

        users = _read_users()

        if any(user['username'] == username for user in users):
            flash('Username already exists.', 'error')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        users.append({'username': username, 'password': hashed_password})
        _write_users(users)

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Legacy admin-only form (no username field submitted)
        if not request.form.get('username') and 'password' in request.form:
            password = request.form.get('password')
            admin_password = os.getenv("ADMIN_PASSWORD")
            if admin_password and password == admin_password:
                user = User("admin", "Admin")
                login_user(user)
                return redirect(url_for('index'))

        username = request.form.get('username')
        password = request.form.get('password')

        users = _read_users()
        user_data = next((user for user in users if user['username'] == username), None)

        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data['username'], user_data['username'])
            login_user(user)
            return redirect(url_for('index'))
        else:
            # Fallback to legacy admin password check if it's the only one
            admin_password = os.getenv("ADMIN_PASSWORD")
            if not users and password == admin_password:
                 user = User("admin", "Admin")
                 login_user(user)
                 return redirect(url_for('index'))

            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/auth/monday')
def monday_login():
    """Redirect to Monday.com OAuth login"""
    if not monday:
        print("[OAUTH] [ERROR] Monday.com OAuth not configured!")
        flash('Monday.com login is not configured. Check your credentials.', 'error')
        return redirect(url_for('login'))
    
    redirect_uri = url_for('monday_callback', _external=True)
    print(f"[OAUTH] Redirecting to Monday.com with URI: {redirect_uri}")
    print(f"[OAUTH] Client ID: {os.getenv('MONDAY_OAUTH_CLIENT_ID')[:20] if os.getenv('MONDAY_OAUTH_CLIENT_ID') else 'NOT SET'}...")
    try:
        return monday.authorize_redirect(redirect_uri)
    except Exception as e:
        print(f"[OAUTH] [ERROR] Error during authorize_redirect: {str(e)}")
        print(traceback.format_exc())
        flash(f'Authentication error: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/auth/monday/callback')
def monday_callback():
    """Handle Monday.com OAuth callback"""
    try:
        print(f"[OAUTH] Monday.com callback received")
        print(f"[OAUTH] Request args: {request.args}")
        
        # Check for errors from Monday.com
        error = request.args.get('error')
        if error:
            error_description = request.args.get('error_description', error)
            print(f"[OAUTH] [ERROR] Error from Monday.com: {error} - {error_description}")
            flash(f'Monday.com authentication failed: {error_description}', 'error')
            return redirect(url_for('login'))
        
        # Get authorization code from callback
        code = request.args.get('code')
        if not code:
            print(f"[OAUTH] [ERROR] No authorization code in callback")
            flash('No authorization code received', 'error')
            return redirect(url_for('login'))
        
        print(f"[OAUTH] Authorization code: {code[:20]}...")
        
        # Manually exchange code for token
        token_data = {
            'client_id': os.getenv('MONDAY_OAUTH_CLIENT_ID'),
            'client_secret': os.getenv('MONDAY_OAUTH_CLIENT_SECRET'),
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': url_for('monday_callback', _external=True)
        }
        
        print(f"[OAUTH] Exchanging code for token...")
        print(f"[OAUTH] Token endpoint: https://auth.monday.com/oauth2/token")
        print(f"[OAUTH] Request data: {json.dumps({k: (v[:20] + '...' if isinstance(v, str) and len(v) > 20 else v) for k, v in token_data.items()}, indent=2)}")
        
        try:
            token_response = requests.post(
                'https://auth.monday.com/oauth2/token',
                data=token_data,
                timeout=10
            )
            print(f"[OAUTH] Token response status: {token_response.status_code}")
            print(f"[OAUTH] Token response: {token_response.text}")
            
            token_response.raise_for_status()
            token = token_response.json()
            
            print(f"[OAUTH] [OK] Token received from Monday.com")
            print(f"[OAUTH] Token keys: {list(token.keys())}")
            
        except requests.exceptions.RequestException as req_error:
            print(f"[OAUTH] [ERROR] Error exchanging code for token: {str(req_error)}")
            print(f"[OAUTH] Response: {req_error.response.text if hasattr(req_error, 'response') and req_error.response else 'No response'}")
            raise
        
        access_token = token.get('access_token')
        if not access_token:
            print(f"[OAUTH] [ERROR] No access token in response: {token}")
            flash('Failed to get access token from Monday.com', 'error')
            return redirect(url_for('login'))

        # Decode JWT payload to extract user identity without an extra API call
        try:
            # JWT format: header.payload.signature
            parts = access_token.split('.')
            if len(parts) != 3:
                raise ValueError("Invalid JWT format")
            
            # Decode payload (add padding if needed)
            payload = parts[1]
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded = base64.urlsafe_b64decode(payload)
            token_claims = json.loads(decoded)
            
            print(f"[OAUTH] [OK] JWT decoded successfully")
            print(f"[OAUTH] Token claims: {json.dumps(token_claims, indent=2)}")
            
            # Extract user info from token claims
            monday_user_id = token_claims.get('uid')  # User ID
            monday_account_id = token_claims.get('actid')  # Account ID
            
            if not monday_user_id:
                print(f"[OAUTH] [ERROR] No user ID in token claims")
                flash('Failed to extract user info from Monday.com token', 'error')
                return redirect(url_for('login'))
            
            print(f"[OAUTH] [OK] User info extracted from token:")
            print(f"[OAUTH]   Monday.com User ID: {monday_user_id}")
            print(f"[OAUTH]   Monday.com Account ID: {monday_account_id}")
            
            # Use user_id as the username (we'll update it if we can get email later)
            username = f"monday_{monday_user_id}"
            name = f"Monday User {monday_user_id}"
            
        except Exception as decode_error:
            print(f"[OAUTH] [ERROR] Error decoding JWT token: {str(decode_error)}")
            print(traceback.format_exc())
            
            # Fallback: Try querying the API anyway
            print(f"[OAUTH] Attempting fallback: querying Monday.com API...")
            query = '{ me { id } }'
            headers = {
                "Authorization": access_token,
                "API-Version": "2023-10",
                "Content-Type": "application/json"
            }
            
            me_response = requests.post('https://api.monday.com/v2', json={'query': query}, headers=headers).json()
            print(f"[OAUTH] Fallback API response: {json.dumps(me_response, indent=2)}")
            
            if me_response.get('errors'):
                error_msg = me_response['errors'][0].get('message', 'Unknown error')
                print(f"[OAUTH] [ERROR] Fallback failed: {error_msg}")
                flash(f'Failed to get Monday.com user info: {error_msg}', 'error')
            return redirect(url_for('login'))
        
        print(f"[OAUTH] [OK] User info retrieved: {username} ({name})")
        print(f"[OAUTH]   Monday.com User ID: {monday_user_id}")
        print(f"[OAUTH]   Monday.com Account ID: {monday_account_id}")
        
        # Create or update user in users.json
        users = _read_users()
        user_db = next((u for u in users if u.get('username') == username), None)
        
        if not user_db:
            # New Monday.com user - create entry
            users.append({
                'username': username,
                'email': username,
                'name': name,
                'monday_id': monday_user_id,
                'monday_account_id': monday_account_id,
                'provider': 'monday',
                'password': None  # OAuth users don't have passwords
            })
            _write_users(users)
            print(f"[OAUTH] [OK] New user created: {username}")
        else:
            # Update existing user
            user_db['monday_id'] = monday_user_id
            user_db['monday_account_id'] = monday_account_id
            user_db['provider'] = 'monday'
            _write_users(users)
            print(f"[OAUTH] [OK] Existing user updated: {username}")
        
        # Store access token for API calls (using Flask session)
        session['monday_token'] = access_token
        session['monday_user_id'] = monday_user_id
        session['monday_account_id'] = monday_account_id
        
        # Login the user
        user = User(username, name)
        login_user(user)
        
        print(f"[OAUTH] [OK] User logged in successfully: {username}")
        flash(f'Welcome {name}!', 'success')
        return redirect(url_for('index'))
    
    except Exception as e:
        print(f"\n[OAUTH] [ERROR] Monday.com OAuth callback ERROR")
        print(f"[OAUTH] Exception Type: {type(e).__name__}")
        print(f"[OAUTH] Exception Message: {str(e)}")
        print(f"[OAUTH] Full Traceback:")
        print(traceback.format_exc())
        print(f"[OAUTH] [ERROR] END ERROR\n")
        flash(f'Authentication failed. Check server logs for details.', 'error')
        return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    linked_items = []
    logs = []
    
    try:
        # 1. Fetch Records from LINKED board for mirroring dropdown
        print(f"[DEBUG] Fetching linked board items with LINK_BOARD = {LINK_BOARD}")
        query_linked = f'{{ boards (ids: {LINK_BOARD}) {{ items_page {{ items {{ id name }} }} }} }}'
        res_link = _monday_graphql(query_linked)
        print(f"[DEBUG] Linked board response: {json.dumps(res_link, indent=2)}")
        
        if res_link.get('data') and res_link['data'].get('boards') and len(res_link['data']['boards']) > 0:
            linked_items = res_link['data']['boards'][0].get('items_page', {}).get('items', [])
            print(f"[DEBUG] Successfully fetched {len(linked_items)} linked items")
        elif res_link.get('errors'):
            error_msg = res_link['errors'][0].get('message', 'Unknown error')
            print(f"[ERROR] API Error: {error_msg}")
            flash(f"API Error fetching linked items: {error_msg}", 'error')
        else:
            print(f"[WARN] Unexpected response structure: {res_link}")
    except Exception as e:
        print(f"[EXCEPTION] Failed to fetch linked items: {str(e)}")
        flash(f"Failed to fetch linked items: {str(e)}", 'error')
    
    try:
        # 2. Fetch Recent Logs from MAIN board
        print(f"[DEBUG] Fetching main board logs with MAIN_BOARD = {MAIN_BOARD}")
        query_main = f'{{ boards (ids: {MAIN_BOARD}) {{ items_page (limit: 10) {{ items {{ name created_at }} }} }} }}'
        res_main = _monday_graphql(query_main)
        print(f"[DEBUG] Main board response: {json.dumps(res_main, indent=2)[:500]}...")
        
        if res_main.get('data') and res_main['data'].get('boards') and len(res_main['data']['boards']) > 0:
            logs = res_main['data']['boards'][0].get('items_page', {}).get('items', [])
            print(f"[DEBUG] Successfully fetched {len(logs)} log items")
        elif res_main.get('errors'):
            error_msg = res_main['errors'][0].get('message', 'Unknown error')
            print(f"[ERROR] API Error: {error_msg}")
            flash(f"API Error fetching logs: {error_msg}", 'error')
        else:
            print(f"[WARN] Unexpected response structure: {res_main}")
    except Exception as e:
        print(f"[EXCEPTION] Failed to fetch logs: {str(e)}")
        flash(f"Failed to fetch logs: {str(e)}", 'error')

    print(f"[DEBUG] Rendering index with {len(linked_items)} linked items and {len(logs)} logs")
    return render_template('index.html', linked_options=linked_items, logs=logs)

def format_column_value(col_id, value):
    """
    Format column values based on Monday.com column types.
    Uses actual column type information provided from the board schema.
    """
    # Skip empty/None values
    if not value or value == '':
        return None
    
    col_id_lower = str(col_id).lower() if col_id else ''
    value_str = str(value).strip()
    
    print(f"    [FORMAT] Column: {col_id}, Value: {repr(value)}")
    
    # ===== TEXT TYPES =====
    if col_id_lower.startswith('text_') or 'text' in col_id_lower:
        result = {"text": value_str}
        print(f"    [FORMAT] -> TEXT: {result}")
        return result
    
    # ===== EMAIL =====
    elif 'email' in col_id_lower:
        # Email columns require both "email" and "text" fields
        result = {"email": value_str, "text": value_str}
        print(f"    [FORMAT] -> EMAIL: {result}")
        return result
    
    # ===== DATETIME (for datetime-local: "2026-03-22T14:30") =====
    elif 'datetime' in col_id_lower:
        if not value_str:
            print(f"    [FORMAT] -> DATETIME: EMPTY, returning None")
            return None
        # datetime-local format comes as "YYYY-MM-DDTHH:mm"
        # Monday.com expects: "YYYY-MM-DD HH:mm:ss" format for GraphQL
        # Convert: 2026-03-22T14:30 -> 2026-03-22 14:30:00
        if 'T' in value_str:
            date_part, time_part = value_str.split('T')
            # Add :00 for seconds if not present
            if time_part.count(':') == 1:
                time_part = f"{time_part}:00"
            value_str = f"{date_part} {time_part}"
        print(f"    [FORMAT] -> DATETIME: '{value_str}'")
        return value_str
    
    # ===== DATE (send as string YYYY-MM-DD) =====
    elif 'date' in col_id_lower:
        if not value_str:
            print(f"    [FORMAT] -> DATE: EMPTY, returning None")
            return None
        # Extract just date part if datetime-local format
        if 'T' in value_str:
            value_str = value_str.split('T')[0]
        print(f"    [FORMAT] -> DATE: '{value_str}'")
        return value_str
    
    # ===== STATUS (like color but for status columns) =====
    elif 'status' in col_id_lower:
        try:
            idx = int(value)
            result = {"index": idx}
            print(f"    [FORMAT] -> STATUS: {result}")
            return result
        except (ValueError, TypeError) as e:
            print(f"    [FORMAT] -> STATUS: FAILED - Could not convert '{value}' to int: {e}")
            return None
    
    # ===== COLOR/STATUS (single_select with index) =====
    elif 'color' in col_id_lower:
        try:
            idx = int(value)
            result = {"index": idx}
            print(f"    [FORMAT] -> COLOR: {result}")
            return result
        except (ValueError, TypeError) as e:
            print(f"    [FORMAT] -> COLOR: FAILED - Could not convert '{value}' to int: {e}")
            return None
    
    # ===== SINGLE SELECT =====
    elif 'single_select' in col_id_lower:
        try:
            # Try as numeric index first
            idx = int(value)
            result = {"index": idx}
            print(f"    [FORMAT] -> SINGLE_SELECT (index): {result}")
            return result
        except (ValueError, TypeError):
            # Fall back to text value
            result = {"text": value_str}
            print(f"    [FORMAT] -> SINGLE_SELECT (text fallback): {result}")
            return result
    
    # ===== BOARD RELATION =====
    elif 'relation' in col_id_lower:
        try:
            item_id = int(value)
            result = {"item_ids": [item_id]}
            print(f"    [FORMAT] -> BOARD_RELATION: {result}")
            return result
        except (ValueError, TypeError) as e:
            print(f"    [FORMAT] -> BOARD_RELATION: FAILED - Could not convert '{value}' to int: {e}")
            return None
    
    # ===== MULTIPLE PERSON =====
    elif 'multiple_person' in col_id_lower or 'person' in col_id_lower:
        try:
            if isinstance(value, list):
                person_ids = [int(v) for v in value]
            else:
                person_id = int(value)
                person_ids = [person_id]
            result = {"personsIds": person_ids}
            print(f"    [FORMAT] -> MULTIPLE_PERSON: {result}")
            return result
        except (ValueError, TypeError) as e:
            print(f"    [FORMAT] -> MULTIPLE_PERSON: FAILED - Could not convert '{value}' to int: {e}")
            return None
    
    # ===== FILE & SIGNATURE (NOT sent via column values - uploaded separately) =====
    elif 'file' in col_id_lower or 'signature' in col_id_lower:
        print(f"    [FORMAT] -> FILE/SIGNATURE: SKIPPED (uploaded separately)")
        return None
    
    # ===== DEFAULT (treat as text) =====
    else:
        result = {"text": value_str}
        print(f"    [FORMAT] -> DEFAULT (text): {result}")
        return result

@app.route('/submit', methods=['POST'])
@login_required
def submit():
    try:
        print(f"\n{'='*80}")
        print(f"[SUBMIT] === NEW FORM SUBMISSION ===")
        print(f"{'='*80}")
        
        # Capture Form Data
        item_name = request.form.get('name')
        linked_id = request.form.get('linked_item_id')
        
        print(f"[SUBMIT] Item name: {repr(item_name)}")
        print(f"[SUBMIT] Linked ID: {repr(linked_id)}")
        
        # Validate required fields
        if not item_name:
            flash('Item name is required', 'error')
            return redirect(url_for('index'))
        
        if not linked_id:
            flash('Please select a Service Request', 'error')
            return redirect(url_for('index'))

        # Build column values - ONLY send non-mirrored fields
        # The board_relation to LINKED_ITEM will trigger automatic mirroring
        # of shared columns like Email, Customer Name, Serial Number, etc.
        form_data = {
            "COL_SERVICE_REQUEST": linked_id,  # THIS triggers the mirror
            # Fields below are NOT auto-mirrored (only exist on MAIN board)
            "COL_EMAIL": request.form.get('email'),  # Primary TSP email
            "COL_SERVICE_START": request.form.get('service_start'),  # Service start datetime
            "COL_SERVICE_END": request.form.get('service_end'),  # Service end datetime
            "COL_LOGIN_DATE": request.form.get('login_date'),  # Log-in datetime
            "COL_LOGOUT_DATE": request.form.get('logout_date'),  # Log-out datetime
            "COL_PROBLEMS": request.form.get('problems'),  # Service specific notes
            "COL_JOB_DONE": request.form.get('job_done'),  # What was completed
            "COL_PARTS_REPLACED": request.form.get('parts_replaced'),
            "COL_RECOMMENDATION": request.form.get('recommendation'),
            "COL_REMARKS": request.form.get('remarks'),  # Additional notes
            "COL_STATUS": request.form.get('status'),
            "COL_TSP_WORKWITH": request.form.get('tsp_workwith'),  # Additional techs
        }
        
        # NOTE: These fields will be AUTO-MIRRORED from LINKED_ITEM:
        # - Customer Name
        # - Customer Email
        # - BIOMED Email
        # - Serial Number
        # - Login/Logout dates
        # - Service Start/End dates
        # DO NOT include them below or it may conflict with the mirror
        
        # Add the logged-in user's name for tracking
        # NOTE: You must add a 'COL_CREATED_BY' variable to your .env file
        # with the column ID from your Monday.com board where the user name will be stored.
        if current_user.is_authenticated:
            user_col_env = "COL_CREATED_BY"
            if os.getenv(user_col_env):
                form_data[user_col_env] = current_user.name
                print(f"[INFO] Item creation will be logged for user: {current_user.name}")
            else:
                print(f"[WARN] '{user_col_env}' is not set in .env. Cannot log creating user.")
        
        # Format column values using the helper function
        column_values = {}
        print(f"\n[DEBUG] === PROCESSING FORM DATA ===")
        for env_var, form_value in form_data.items():
            col_id = os.getenv(env_var)
            if col_id:
                print(f"[DEBUG] Processing {env_var}:")
                print(f"  Column ID: {col_id}")
                print(f"  Form Value: {repr(form_value)}")
                print(f"  Value Type: {type(form_value).__name__}")
                try:
                    formatted_value = format_column_value(col_id, form_value)
                    if formatted_value is not None:
                        column_values[col_id] = formatted_value
                        print(f"  [OK] FORMATTED TO: {formatted_value}")
                    else:
                        print(f"  [OK] SKIPPED (None/Empty)")
                except Exception as format_error:
                    print(f"  [ERROR] ERROR FORMATTING: {str(format_error)}")
                    print(f"  Stack trace: {format_error}")
            else:
                print(f"[DEBUG] {env_var} - ENV VAR NOT SET, SKIPPING")
        
        print(f"\n[DEBUG] === FINAL COLUMN VALUES TO SEND ===")
        print(f"[DEBUG] Total columns to send: {len(column_values)}")
        for col_id, val in column_values.items():
            env_name = next((k for k, v in os.environ.items() if v == col_id and k.startswith('COL_')), 'UNKNOWN')
            print(f"[DEBUG] {env_name} ({col_id}): {val}")

        # 1. Create the Item with only the fields that have values
        create_query = """
        mutation ($boardId: ID!, $itemName: String!, $columnVals: JSON!) {
            create_item (board_id: $boardId, item_name: $itemName, column_values: $columnVals) { id }
        }
        """
        
        print(f"\n[DEBUG] === SENDING MUTATION ===")
        print(f"[DEBUG] Board ID: {MAIN_BOARD}")
        print(f"[DEBUG] Item Name: {item_name}")
        print(f"[DEBUG] Column Values (as object):")
        print(json.dumps(column_values, indent=2))
        
        # GraphQL JSON type requires a JSON string (not a Python object)
        # Ensure all values are JSON-compatible before serialization
        for col_id, val in column_values.items():
            if val is not None and not isinstance(val, (str, int, float, bool, dict, list)):
                print(f"[WARN] Column {col_id} has non-JSON-compatible type: {type(val).__name__}")
        
        column_vals_json = json.dumps(column_values)
        print(f"[DEBUG] Column values JSON string: {column_vals_json}")

        gql_vars = {
            "boardId": MAIN_BOARD,
            "itemName": item_name,
            "columnVals": column_vals_json  # Must be a JSON string for Monday.com GraphQL
        }
        print(f"[DEBUG] GraphQL Variables (type-checked):")
        for k, v in gql_vars.items():
            print(f"[DEBUG]   {k}: {type(v).__name__} = {repr(v)[:100]}")
        print(f"[DEBUG] Full GraphQL Variables JSON:")
        print(f"[DEBUG] {json.dumps(gql_vars, indent=2)}")

        res = _monday_graphql(create_query, gql_vars)
        
        print(f"\n[DEBUG] === API RESPONSE ===")
        print(json.dumps(res, indent=2))
        
        if res.get('errors'):
            error_msg = res['errors'][0].get('message', 'Unknown error')
            error_details = res['errors'][0]
            print(f"\n[ERROR] === API ERROR DETAILS ===")
            print(f"[ERROR] Message: {error_msg}")
            print(f"[ERROR] Full Error Object:\n{json.dumps(error_details, indent=2)}")
            print(f"\n[ERROR] === PROBLEMATIC COLUMNS ===")
            print(f"[ERROR] Column values that were sent:")
            for col_id, val in column_values.items():
                env_name = next((k for k, v in os.environ.items() if v == col_id and k.startswith('COL_')), 'UNKNOWN')
                print(f"[ERROR]   {env_name} ({col_id}): {val}")
            
            flash(f"API Error: {error_msg}", 'error')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': f'API Error: {error_msg}'})
            return redirect(url_for('index'))
        
        if 'data' in res and res['data'].get('create_item'):
            item_id = res['data']['create_item']['id']
            print(f"[SUCCESS] Created item with ID: {item_id}")

            # Check if AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            if is_ajax:
                return jsonify({'success': True, 'item_id': item_id, 'item_name': item_name})
            else:
                flash(f"Success! Service entry '{item_name}' created (ID: {item_id}).", 'success')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Failed to create item. Check data and try again.'})
            flash("Error creating item. Please check your data and try again.", 'error')
    
    except ValueError as e:
        print(f"\n[ERROR] === VALUE ERROR ===")
        print(f"[ERROR] Message: {str(e)}")
        print(f"[ERROR] Type: {type(e).__name__}")
        print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
        flash(f"Invalid data format: {str(e)}", 'error')
    except TypeError as e:
        print(f"\n[ERROR] === TYPE ERROR ===")
        print(f"[ERROR] Message: {str(e)}")
        print(f"[ERROR] Type: {type(e).__name__}")
        print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
        flash(f"Type error: {str(e)}", 'error')
    except Exception as e:
        print(f"\n[ERROR] === UNEXPECTED ERROR ===")
        print(f"[ERROR] Message: {str(e)}")
        print(f"[ERROR] Type: {type(e).__name__}")
        print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
        flash(f"Unexpected error: {str(e)}", 'error')
    finally:
        print(f"[SUBMIT] === SUBMISSION COMPLETE ===\n")
    
    return redirect(url_for('index'))

def upload_file_to_monday_bytes(item_id, column_id, file_data, filename):
    """
    Upload binary PNG data to a Monday.com file/image column via multipart GraphQL.
    """
    try:
        print(f"\n[SIGNATURE] === Uploading {filename} ===")
        print(f"[SIGNATURE] Item ID: {item_id}, Column ID: {column_id}, Size: {len(file_data)} bytes")
        sys.stdout.flush()

        # Save to temp file (requests needs a file object)
        tmp_path = os.path.join(tempfile.gettempdir(), f"{item_id}_{filename}")
        with open(tmp_path, 'wb') as f:
            f.write(file_data)

        mutation = 'mutation ($file: File!) { add_file_to_column (item_id: %s, column_id: "%s", file: $file) { id } }' % (item_id, column_id)
        print(f"[SIGNATURE] Mutation: {mutation}")

        # Monday.com expects the query as a JSON-encoded value, same as regular API calls
        query_json = json.dumps({"query": mutation})

        with open(tmp_path, 'rb') as f:
            res = requests.post(
                FILE_URL,
                headers=HEADERS,
                files={
                    'query': (None, query_json, 'application/json'),
                    'variables[file]': (filename, f, 'image/png'),
                },
                timeout=30,
            )

        print(f"[SIGNATURE] Response status: {res.status_code}")
        print(f"[SIGNATURE] Response: {res.text[:500]}")

        # Cleanup temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        try:
            resp_json = res.json()
        except Exception:
            return False, f'No valid JSON response: {res.text[:200]}'

        if resp_json.get('errors'):
            err_msg = resp_json['errors'][0].get('message', 'Unknown error')
            print(f"[SIGNATURE] ERROR: {err_msg}")
            return False, err_msg

        if resp_json.get('error_message'):
            print(f"[SIGNATURE] ERROR: {resp_json['error_message']}")
            return False, resp_json['error_message']

        if resp_json.get('data') and resp_json['data'].get('add_file_to_column'):
            file_id = resp_json['data']['add_file_to_column'].get('id')
            print(f"[SIGNATURE] SUCCESS! File ID: {file_id}")
            return True, file_id

        return False, f'Unexpected response: {str(resp_json)[:200]}'

    except Exception as e:
        print(f"[SIGNATURE] ERROR: {str(e)}")
        print(traceback.format_exc())
        return False, str(e)


# Signature key -> Monday.com column ID mapping
SIG_COLUMN_MAP = {
    'sig_tsp': os.getenv("COL_TSP_SIGNATURE"),
    'sig_customer': os.getenv("COL_CUSTOMER_SIGNATURE"),
    'sig_biomed': os.getenv("COL_BIOMED_SIGNATURE"),
    'sig_tsp_workwith': os.getenv("COL_TSP_WORKWITH_SIGNATURE"),
}

@app.route('/api/upload_signature', methods=['POST'])
@login_required
def api_upload_signature():
    """
    AJAX endpoint: Upload a signature PNG file to a Monday.com item column.
    Expects multipart form data with: file (PNG), item_id, sig_key
    """
    try:
        item_id = request.form.get('item_id')
        sig_key = request.form.get('sig_key')
        file = request.files.get('file')

        print(f"\n[API SIG] === Upload Request ===")
        print(f"[API SIG] item_id={item_id}, sig_key={sig_key}, file={'yes' if file else 'no'}")

        if not item_id or not sig_key or not file:
            return jsonify({'success': False, 'error': 'Missing item_id, sig_key, or file'}), 400

        column_id = SIG_COLUMN_MAP.get(sig_key)
        if not column_id:
            return jsonify({'success': False, 'error': f'Unknown sig_key: {sig_key}. Check .env column IDs.'}), 400

        # Read file bytes from the upload
        file_data = file.read()
        if len(file_data) < 100:
            return jsonify({'success': False, 'error': 'File too small - likely empty signature'}), 400

        print(f"[API SIG] File size: {len(file_data)} bytes, Column: {column_id}")

        filename = f"{sig_key}_{item_id}.png"
        success, result = upload_file_to_monday_bytes(item_id, column_id, file_data, filename)

        if success:
            return jsonify({'success': True, 'file_id': result})
        else:
            return jsonify({'success': False, 'error': result})

    except Exception as e:
        print(f"[API SIG] ERROR: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/search_linked_items')
@login_required
def search_linked_items():
    """Search for linked items in real-time based on user query."""
    query_param = request.args.get('q', '').lower().strip()
    
    try:
        # Fetch all items from the linked board with increased limit
        # Monday.com API limit: max 500 items per page
        query_linked = f'{{ boards (ids: {LINK_BOARD}) {{ items_page (limit: 500) {{ items {{ id name }} }} }} }}'
        res_link = _monday_graphql(query_linked)
        
        all_items = []
        if res_link.get('data') and res_link['data'].get('boards') and len(res_link['data']['boards']) > 0:
            all_items = res_link['data']['boards'][0].get('items_page', {}).get('items', [])
            print(f"[DEBUG] Fetched {len(all_items)} items from LINKED_BOARD {LINK_BOARD}")
        elif res_link.get('errors'):
            print(f"[ERROR] Monday.com API Error: {res_link['errors'][0].get('message', 'Unknown error')}")
        
        # Filter items based on search query
        if query_param:
            items = [item for item in all_items if query_param in item.get('name', '').lower()]
            print(f"[DEBUG] Filtered to {len(items)} items matching '{query_param}'")
        else:
            items = all_items
        
        # Format response for Select2
        results = [{'id': item['id'], 'text': item['name']} for item in items[:100]]  # Limit results to 100 for UI performance
        return jsonify({'results': results})
    
    except Exception as e:
        print(f"[ERROR] Search failed: {str(e)}")
        return jsonify({'results': []})

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', message="Internal server error"), 500

@app.errorhandler(403)
def forbidden(error):
    return render_template('error.html', message="Access forbidden"), 403

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
