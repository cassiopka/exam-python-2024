from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from mysql_db import MySQL
import mysql.connector
import math

app = Flask(__name__)
application = app
app.config.from_pyfile('config.py')

db = MySQL(app)

from auth import bp_auth, check_rights, init_login_manager
from review import bp_review
from book import bp_book

app.register_blueprint(bp_auth)
app.register_blueprint(bp_review)
app.register_blueprint(bp_book)

init_login_manager(app)

PER_PAGE = 3

@app.route('/')
def index():
    books=[]
    query = '''
        SELECT b.*, GROUP_CONCAT(g.name SEPARATOR ', ') AS genres
        FROM books b
        LEFT JOIN books_genres bg ON b.id = bg.book_id
        LEFT JOIN genres g ON bg.genre_id = g.id
        GROUP BY b.id
        ORDER BY b.year DESC;'''
    page = int(request.args.get('page', 1))
    count = 0
    try:
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query)
            books = cursor.fetchall()
        count = math.ceil(len(books) / PER_PAGE)
    except mysql.connector.errors.DatabaseError as err:
        db.connection().rollback()
        flash(f'Произошла ошибка при загрузке страницы! {err}', 'danger')
    return render_template('index.html', books=books[PER_PAGE * (page - 1) : PER_PAGE * page], count=count, page=page)
