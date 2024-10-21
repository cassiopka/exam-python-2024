from flask import Flask, render_template, request, session, redirect, url_for, flash, Blueprint
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from mysql_db import MySQL
from app import db
from auth import check_rights
from check_user import CheckUser
import mysql.connector
import math

bp_book = Blueprint('book', __name__, url_prefix='/book')

def get_user():
    query = 'SELECT * FROM users'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    user = cursor.fetchall()
    cursor.close()
    return user

def get_genres():
    query = 'SELECT * FROM genres'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    genre = cursor.fetchall()
    cursor.close()
    return genre

def get_genres_of_book(book_id):
    query = 'SELECT genres.name FROM genres JOIN books_genres ON genres.id = books_genres.genre_id WHERE books_genres.book_id = %s'
    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (book_id,))
        genres = [row.name for row in cursor.fetchall()]
    return genres

@bp_book.route('/books/show/<int:book_id>')
@check_rights('show')
def show_book(book_id):
    user = get_user()
    query = '''
        SELECT b.*, GROUP_CONCAT(g.name SEPARATOR ', ') AS genres
        FROM books b
        LEFT JOIN books_genres bg ON b.id = bg.book_id
        LEFT JOIN genres g ON bg.genre_id = g.id
        WHERE b.id = %s
        GROUP BY b.id
        ORDER BY b.year DESC;'''
    
    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (book_id,))
        book = cursor.fetchone()

    review_query = "SELECT * FROM reviews WHERE book = %s AND user = %s"
    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(review_query, (book_id, current_user.get_id()))
        review = cursor.fetchone()

    return render_template('books/show.html', book=book, user=user, review=review, review_id=review.id if review else None, book_id=book_id)

@bp_book.route('/books/create', methods=["POST", "GET"])
@check_rights('create')
def create():
    genres = get_genres()
    if request.method == 'POST':
        name = request.form['name']
        author = request.form['author']
        description = request.form['description']
        year = request.form['year']
        publishing = request.form['publishing']
        pages = request.form['pages']
        genre_ids = request.form.getlist('genre_id')

        try:
            query = 'INSERT INTO books (name, author, description, year, publishing, pages, image) VALUES (%s, %s, %s, %s, %s, %s, 1)'
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query, (name, author, description, year, publishing, pages))
            book_id = cursor.lastrowid
            for genre_id in genre_ids:
                query = 'INSERT INTO books_genres (book_id, genre_id) VALUES (%s, %s)'
                cursor.execute(query, (book_id, genre_id))
            db.connection().commit()
            flash(f'Книга "{name}" успешно добавлена!', 'success')
            cursor.close()
            return redirect(url_for('index'))
        
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При создании книги произошла ошибка!', 'danger')
            return render_template('books/create.html', genres=genres)
    return render_template('books/create.html', genres=genres)

@bp_book.route('/books/edit/<int:book_id>', methods=["POST", "GET"])
@check_rights('edit')
def edit(book_id):
    genres = get_genres()
    if request.method == 'POST':
        name = request.form['name']
        author = request.form['author']
        description = request.form['description']
        year = request.form['year']
        publishing = request.form['publishing']
        pages = request.form['pages']
        genre_ids = request.form.getlist('genre_id')

        try:
            query = 'UPDATE books set name = %s, author = %s, description = %s, year = %s, publishing = %s, pages = %s, image = 1 where id = %s'
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query, (name, author, description, year, publishing, pages, book_id))
            db.connection().commit()
            query = 'DELETE FROM books_genres WHERE book_id = %s'
            cursor.execute(query, (book_id,))
            db.connection().commit()
            for genre_id in genre_ids:
                query = 'INSERT INTO books_genres (book_id, genre_id) VALUES (%s, %s)'
                cursor.execute(query, (book_id, genre_id,))
                db.connection().commit()
            flash(f'Данные книги "{name}" успешно обновлены!', 'success')
            cursor.close()
            return redirect(url_for('index', genres=genres))
        
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash(f'При обновлении данных о книге произошла ошибка!', 'danger')
            return render_template('books/edit.html', genres=genres)
        
    query = 'SELECT * FROM books WHERE books.id=%s'
    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (book_id,))
        book = cursor.fetchone()
    return render_template('books/edit.html', book=book, genres=genres)

@bp_book.route('/books/delete/')
@login_required
@check_rights('delete')
def delete():
    user = get_user()
    book_id = request.args.get('book_id')
    try:
        query = 'DELETE FROM reviews WHERE book = %s'
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (book_id,))
        db.connection().commit()

        query = 'DELETE FROM books_genres WHERE book_id = %s'
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (book_id,))
        db.connection().commit()

        query = 'DELETE from books where id = %s'
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (book_id,))
        db.connection().commit()

        flash(f'Книга успешно удалена!', 'success')
        cursor.close()

    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'При удалении книги произошла ошибка.', 'danger')
        return render_template('index.html', book_id=book_id, user=user)

    return redirect(url_for('index'))