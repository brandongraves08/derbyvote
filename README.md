# Pinewood Derby Voter

A web application for managing and voting on pinewood derby cars. This application provides two main interfaces:

1. **Admin Interface**
   - Upload pictures of pinewood derby cars
   - Add car details (car number, owner name, etc.)
   - Manage the voting session

2. **Public Voting Interface**
   - View all participating cars
   - Vote for favorite cars
   - Real-time voting results

## Technical Stack

- Backend: Python Flask
- Frontend: HTML5, CSS3, JavaScript
- Database: SQLite
- Image Storage: Local filesystem

## Setup and Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the database:
   ```bash
   flask init-db
   ```

4. Run the application:
   ```bash
   flask run
   ```

## Project Structure

```
pinewood-derby-voter/
├── static/
│   ├── css/
│   ├── js/
│   └── uploads/
├── templates/
├── instance/
├── app.py
├── schema.sql
├── requirements.txt
└── README.md
```

## Features

- Secure admin interface with login
- Image upload and storage
- Real-time voting system
- Mobile-responsive design
- Vote tracking to prevent duplicate votes
- Results dashboard

## Security

- Admin authentication required for car management
- Session-based voting to prevent duplicate votes
- Input validation and sanitization
- Secure file upload handling

## License

MIT License
