#Import required libraries
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, session 
from flask_socketio import SocketIO, emit, join_room 
import secrets


#Create a database connection
def get_db_connection():
    conn = sqlite3.connect('collaboration.db')
    conn.row_factory = sqlite3.Row
    return conn

#Initialize the database with required tables
def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL DEFAULT 'Untitled Document',
        content TEXT,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
        
    ''')
    conn.commit()
    conn.close()
    print ("Database initialized successfully")


#Initialize Flask application
app = Flask(__name__)
#Generate a secure random key for session management
app.config['SECRET_KEY'] = secrets.token_hex(16)
#Initialize SocketIO with CORS enabled for all origins
socketio = SocketIO(app, cors_allowed_origins="*")

#In-memory storage for active documents
#Format: {doc_id: {'content': string, 'users': [user_ids]}}
documents = {}

#In-memory storage for connected users
#Format: {user_id: {'username': string, 'document': doc_id or None}}
users = {}



@app.route('/')
def index():
    """
    Route for the home page.
    Returns the rendered index.html template.
    """
    return render_template('index.html')

@app.route('/document/<doc_id>')
def document(doc_id):
    """
    Route for a specific document page.
    
    Args:
        doc_id (str): The unique identifier for the document
        
    Returns:
        The rendered document.html template with the doc_id and username
    """

    #Get the username from the query parameters, default to "Anonymous"
    username = request.args.get('username', 'Anonymous')
    #Store the username in the session for later use
    session['username'] = username
    
    # Check if document exists in database
    conn =  get_db_connection()
    doc = conn.execute('SELECT * FROM documents where id = ?', (doc_id,)).fetchone()
    
    if not doc:
        # Create new document in database
        now = datetime.now()
        conn.execute(
            'INSERT INTO documents (id, title, content, created_at, updated_at) VALUES (?,?,?,?,?)',
            (doc_id, f"Document {doc_id[:5]}", "", now,now)
        )
    conn.commit()
    
    #Initialize in memory
    #Initialize in memory
    if doc_id not in documents:
        if doc:  # If document exists in database, use its content
            documents[doc_id] = {
                'content': doc['content'],
                'users': []
            }
        else:  # Otherwise use empty content
            documents[doc_id] = {
                'content': '',
                'users': []
            }
    conn.close()
    
    #Render document template
    return render_template('document.html', doc_id=doc_id, username = username)


@app.route('/dashboard')
def dashboard():
    username = request.args.get('username', 'Anonymous')
    
    # Get all documents from database
    conn = get_db_connection()
    database_docs = conn.execute(
        'SELECT id, title, updated_at FROM documents ORDER BY updated_at DESC'
    ).fetchall()
    conn.close()
    
    # Convert SQLite Row objects to dictionaries to avoid any potential issues
    document_dicts = []
    for doc in database_docs:
        document_dicts.append({
            'id': doc['id'],
            'title': doc['title'],
            'updated_at': doc['updated_at']
        })
    
    # Print debug info
    print(f"Type of document_dicts: {type(document_dicts)}")
    print(f"Length of document_dicts: {len(document_dicts)}")
    
    return render_template('dashboard.html', document_dicts=document_dicts, username=username)
    

@socketio.on('connect')
def handle_connect():
    """
    Socket.IO event handler for new connections.
    Called automatically when a client connects via Socket.IO
    """
    #Get the Socket.IO session ID for this connection
    user_id = request.sid
    #Get the username from the Flask session
    username = session.get('username','Anonymous')
    
    # Store the user information
    users[user_id] = {
        'username': username,
        'document': None #Not in any document yet
    }
    
    # Send a confirmation to the client that they're connected
    emit('connected', {'user_id': user_id, 'username': username})
    

@socketio.on('join_document')
def handle_join_document(data):
    """
    Socket.IO event handler for a user joining a document.
    
    Args:
        data (dict): Contains the doc_id for the document to join
    """
    # Get the Socket.IO session ID for this connection
    user_id = request.sid
    # Get the document ID from the data
    doc_id = data['doc_id']
    
    # Add user to document if the document exists
    if doc_id in documents:
        # Add this user to the document's user list if not already there
        if user_id not in documents[doc_id]['users']:
            documents[doc_id]['users'].append(user_id)
            
        
        # update the user's current document reference
        users[user_id]['document'] = doc_id
        
        # Join the Socket.io room for this document
        # This allows broadcasting messages only to users in this document
        join_room(doc_id)
        
        # Send the current document content to the user
        # Also send the list of usernames currently in this document
        emit('document_content', {
            'content':documents[doc_id]['content'],
            'users': [users[uid]['username'] for uid in documents[doc_id]['users'] if uid in users]
        })
        
        # Notify other users in the document that a new user has joined
        emit('user_joined',{
            'username': users[user_id]['username']
        }, to=doc_id, include_self = False) # 'to=doc_id' sends only to the document room
        

@socketio.on('update_content')
def handle_update_content(data):
    """
    Socket.IO event handler for document content updates.
    
    Args:
        data (dict): Contains the new content for the document
        
    """
    # Get the Socket.IO session ID for this connection
    user_id = request.sid
    # Get the document ID this user is currently editing
    doc_id = users[user_id]['document']
    
    # update document content if the user is in a valid document
    if doc_id and doc_id in documents:
        # Update the document content with the new content
        documents[doc_id]['content'] = data['content']
        
        
        #save to database
        conn = get_db_connection()
        conn.execute(
            'UPDATE documents SET content = ?, updated_at = ? WHERE id = ?',
            (data['content'], datetime.now(), doc_id)
        )
        conn.commit()
        conn.close()
        
        # Broadcast the change to all other users in the document
        emit('content_changed', {
            'content': data['content'],
            'username': users[user_id]['username']
        }, to=doc_id, include_self=False)  # Don't send back to the sender
        

@socketio.on('cursor_move')
def handle_cursor_move(data):
    """
    Socket.IO event handler for cursor position updates.
    
    Args:
        data (dict): Contains the cursor position
    """
    #Get the socket.IO session ID for this connection
    user_id = request.sid
    # Get the document ID this user is currently editing
    doc_id = users[user_id]['document']
    
    # Broadcast cursor position if the user is in a valid document
    if doc_id and doc_id in documents:
        # Send cursor position to all other users in the document
        emit ('cursor_update', {
            'position': data['position'],
            'username': users[user_id]['username'],
            'user_id': user_id
        }, to=doc_id, include_self=False) #Dont send back to the sender
        

@socketio.on('disconnect')
def handle_disconnect():
    """
    Socket.IO event handler for disconnections.
    Called automatically when a client disconnects.
    """
    # Get the socket.io session ID for this connection
    user_id = request.sid
    
    # Clean up user data if the user exists
    if user_id in users:
        #Get the document ID this user was editing
        doc_id = users[user_id]['document']
        # Get the username for notifications
        username = users[user_id]['username']
        
        #Remove user from document if they were in one
        if doc_id and doc_id in documents:
            if user_id in documents[doc_id]['users']:
                documents[doc_id]['users'].remove(user_id)
                
            # Notify other users that this user has left
            emit ('user_left',{
                'username': username
            }, to=doc_id)
            
            # Remove empty documents to clean up memory
            if not documents[doc_id]['users']:
                del documents[doc_id]
                
        #Remove the user from the users dictionary
        del users[user_id]
        
#Run the application if this file is executed directly
if __name__ == '__main__':
    #initialize the database
    init_db()
    #start the socket.io server
    socketio.run(app, debug=True)
        
    
