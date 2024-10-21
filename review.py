from flask import Flask, render_template, request, redirect, url_for, flash, Blueprint
from flask_login import login_required, current_user
from app import db
from auth import check_rights
from mysql_db import MySQL
from check_user import CheckUser
import mysql.connector

bp_review = Blueprint('review', __name__, url_prefix='/review')

@bp_review.route('/review/<int:book_id>', methods=['GET', 'POST'])
@login_required
def review(book_id):
    try:
        query = "SELECT * FROM reviews WHERE book = %s AND user = %s"
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (book_id, current_user.get_id()))
        review = cursor.fetchone()
        if review:
            cursor.close()
            flash(f'Вы уже оставили рецензию на данную книгу!', 'danger')
            return redirect(url_for('book.show_book', book_id=book_id))

        if request.method == 'POST':
            text = request.form.get('review')
            rate = int(request.form.get('rate'))
            query1 = "INSERT INTO reviews (rate, text, book, user) VALUES (%s, %s, %s, %s)"
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute(query1, (rate, text, book_id, current_user.get_id()))

            query2 = "SELECT COUNT(*) as review_count, AVG(rate) as avg_rate FROM reviews WHERE book = %s"
            cursor.execute(query2, (book_id,))
            result = cursor.fetchone()
            review_count = result.review_count
            avg_rate = result.avg_rate

            query3 = "UPDATE books SET rating_count = %s, rating_sum = %s WHERE id = %s"
            cursor.execute(query3, (review_count, avg_rate, book_id))
            db.connection().commit()
            cursor.close()
            flash(f'Рецензия была успешно добавлена!', 'success')
            return redirect(url_for('book.show_book', book_id=book_id))

        if request.method == 'GET':
            cursor = db.connection().cursor(named_tuple=True)
            cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
            book = cursor.fetchone()
            cursor.close()
            return render_template('books/review.html', book=book)
        
    except mysql.connector.errors.DatabaseError as err:
        db.connection().rollback()
        flash(f'Произошла ошибка!: {err}', 'danger')
        return redirect(url_for('book.show_book', book_id=book_id))

@bp_review.route('/review/delete_review/<int:review_id>')
@login_required
def delete_review(review_id):
    try:
        query = "SELECT * FROM reviews WHERE id = %s AND user = %s"
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (review_id, current_user.get_id()))
        review = cursor.fetchone()

        if not review:
            flash(f'Вы не можете удалить эту рецензию!', 'danger')
            return redirect(url_for('book.show_book', book_id=review.book))

        query = "DELETE FROM reviews WHERE id = %s"
        cursor.execute(query, (review_id,))
        db.connection().commit()
        cursor.close()

        flash(f'Рецензия была успешно удалена!', 'success')
        return redirect(url_for('book.show_book', book_id=review.book))

    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash(f'Произошла ошибка при удалении рецензии!', 'danger')
        return redirect(url_for('book.show_book', book_id=review.book))

@bp_review.route('/reviews/<int:book_id>')
def show_reviews(book_id):
    try:
        query = "SELECT * FROM books WHERE id = %s"
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (book_id,))
        book = cursor.fetchone()
        query = "SELECT r.*, u.first_name, u.last_name, u.middle_name FROM reviews r JOIN users u ON r.user = u.id WHERE r.book = %s"
        cursor.execute(query, (book_id,))
        reviews = cursor.fetchall()
        cursor.close()
        return render_template('books/reviews.html', book=book, book_id=book_id, reviews=reviews)

    except mysql.connector.errors.DatabaseError as err:
        db.connection().rollback()
        flash(f'Произошла непредвиденная ошибка!: {err}', 'danger')
        return redirect(url_for('book.show_book', book_id=book_id))