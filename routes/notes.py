from flask import Blueprint, render_template, request, jsonify, session
from extensions import db
from models.user import User
from models.note import Note
from datetime import datetime
from sqlalchemy import text

notes_bp = Blueprint('notes', __name__, url_prefix='/apps/notes')

@notes_bp.route('/')
def notes():
    """Render notes page with all notes"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
        
    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    user_id = request.args.get('user_id', current_user.id)
    
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        user_id = current_user.id

    all_notes = Note.query.filter_by(user_id=user_id).order_by(Note.created_at.desc()).all()
    print(f"Loading notes page - Found {len(all_notes)} notes for user {user_id}")
    
    return render_template('notes.html', notes=all_notes, current_user_id=current_user.id)

@notes_bp.route('/create', methods=['POST'])
def create_note():
    """Create a new note - Intentionally vulnerable to XSS"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
        
    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    title = request.form.get('title')
    content = request.form.get('content')
    
    if not title or not content:
        return jsonify({'success': False, 'error': 'Title and content are required'}), 400
    
    try:
        print(f"Creating note - Title: {title}, Content: {content}")
        
        note = Note(
            title=title,
            content=content,
            created_at=datetime.now(),
            user_id=current_user.id
        )
        
        db.session.add(note)
        db.session.commit()
        
        print(f"Note created with ID: {note.id}")
        
        return jsonify({
            'success': True,
            'message': 'Note created successfully',
            'note': {
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': note.user_id
            }
        })
    except Exception as e:
        print(f"Error creating note: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@notes_bp.route('/search')
def search_notes():
    """Secure search function - Prevents SQL Injection"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    query = request.args.get('q', '').strip()  # Sanitize input

    print(f"Search query: {query}")

    try:
        if not query:
            return jsonify({'success': False, 'error': 'Search query cannot be empty'}), 400

        # Use SQLAlchemy ORM (preferred approach)
        notes = Note.query.filter(
            (Note.title.ilike(f"%{query}%")) | (Note.content.ilike(f"%{query}%"))
        ).filter_by(user_id=current_user.id).all()  # Ensure the user only searches their own notes

        notes_list = []
        for note in notes:
            notes_list.append({
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': note.user_id
            })

        print(f"Found {len(notes_list)} matching notes")
        return jsonify({'success': True, 'notes': notes_list})

    except Exception as e:
        print(f"Error searching notes: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    

@notes_bp.route('/delete/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a note with intentional access control vulnerability"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
        
    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    try:
        note = Note.query.get(note_id)
        if not note:
            print(f"Note not found: {note_id}")
            return jsonify({'success': False, 'error': f'Note with ID {note_id} not found'}), 404
        
        print(f"Deleting note ID: {note_id}, Title: {note.title}, Owner: {note.user_id}")
        
        db.session.delete(note)
        db.session.commit()
        
        print(f"Note {note_id} deleted successfully")
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting note: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@notes_bp.route('/debug')
def debug_database():
    """Debug route to check database contents"""
    try:
        users = User.query.all()
        print("\nAll Users:")
        for user in users:
            print(f"ID: {user.id}, Username: {user.username}")
        
        notes = Note.query.all()
        print("\nAll Notes:")
        for note in notes:
            print(f"ID: {note.id}, Title: {note.title}, User ID: {note.user_id}")
        
        sql = text("SELECT * FROM notes")
        result = db.session.execute(sql)
        rows = result.fetchall()
        print("\nRaw SQL Notes Query Result:")
        for row in rows:
            print(row)
            
        return jsonify({
            'users': [{'id': u.id, 'username': u.username} for u in users],
            'notes': [note.to_dict() for note in notes]
        })
    except Exception as e:
        print(f"Debug Error: {e}")
        return jsonify({'error': str(e)}), 500
    