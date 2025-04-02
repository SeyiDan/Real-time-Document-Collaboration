# Real-Time Collaborative Document Editor

A web-based document editor that allows multiple users to collaborate on documents in real-time. This application provides synchronized editing, cursor tracking, and user presence awareness.

## Features

- **Real-time collaboration**: Multiple users can edit the same document simultaneously
- **Live cursor tracking**: See where other users are editing in real-time
- **User presence**: View a list of active users in each document
- **Persistent storage**: Documents are saved to a SQLite database
- **Document dashboard**: Browse and access all created documents
- **Easy sharing**: Copy document links to invite collaborators

## Technologies Used

- **Backend**: Python with Flask and Flask-SocketIO
- **Frontend**: HTML, CSS, JavaScript
- **Real-time communication**: Socket.IO
- **Database**: SQLite

## Installation

### Prerequisites

- Python 3.6+
- pip (Python package manager)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/collaborative-editor.git
   cd collaborative-editor
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install flask flask-socketio sqlite3
   ```

4. Initialize the database:
   ```
   python app.py
   ```

## Usage

1. Start the application:
   ```
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Create a new document or join an existing one by entering its ID.

## Project Structure

- `app.py`: Main Flask application and Socket.IO event handlers
- `templates/`
  - `index.html`: Homepage with options to create or join documents
  - `document.html`: The collaborative editor interface
  - `dashboard.html`: List of all available documents
- `collaboration.db`: SQLite database storing document information

## How It Works

### Document Creation and Storage

When a user creates a new document, a random ID is generated and the document is stored in the SQLite database. The document can be accessed by its unique ID.

### Real-time Collaboration

The application uses Socket.IO to:
- Broadcast document changes to all connected users
- Notify when users join or leave a document
- Track and display cursor positions for each active user

### Socket.IO Events

- `connect`: Triggered when a user connects to the server
- `join_document`: Adds a user to a specific document session
- `update_content`: Broadcasts content changes to all users in a document
- `cursor_move`: Broadcasts cursor position updates
- `disconnect`: Handles cleanup when a user disconnects

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
