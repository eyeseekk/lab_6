from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import db, Course, Category, User, Review
from tools import CoursesFilter, ImageSaver

bp = Blueprint('courses', __name__, url_prefix='/courses')

COURSE_PARAMS = ['author_id', 'name', 'category_id', 'short_desc', 'full_desc']
REVIEWS_PER_PAGE = 10


def params():
    return {p: request.form.get(p) or None for p in COURSE_PARAMS}


def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': [x for x in request.args.getlist('category_ids') if x],
    }


@bp.route('/')
def index():
    courses = CoursesFilter(**search_params()).perform()
    pagination = db.paginate(courses)
    courses = pagination.items
    categories = db.session.execute(db.select(Category)).scalars()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())


@bp.route('/new')
@login_required
def new():
    course = Course()
    categories = db.session.execute(db.select(Category)).scalars()
    users = db.session.execute(db.select(User)).scalars()
    return render_template('courses/new.html', course=course, categories=categories, users=users)


@bp.route('/create', methods=['POST'])
@login_required
def create():
    f = request.files.get('background_img')
    if f and f.filename:
        img = ImageSaver(f).save()
    else:
        flash('Необходимо загрузить фоновое изображение', 'danger')
        return redirect(url_for('courses.new'))

    course = Course(**params(), background_image_id=img.id)
    try:
        db.session.add(course)
        db.session.commit()
        flash(f'Курс "{course.name}" успешно создан!', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Произошла ошибка при создании курса.', 'danger')
        return redirect(url_for('courses.new'))

    return redirect(url_for('courses.index'))


@bp.route('/<int:course_id>')
def show(course_id):
    course = db.get_or_404(Course, course_id)

    # 5 последних отзывов
    reviews = db.session.execute(
        db.select(Review)
        .where(Review.course_id == course_id)
        .order_by(Review.created_at.desc())
        .limit(5)
    ).scalars().all()

    # проверка отзыва
    user_review = None
    if current_user.is_authenticated:
        user_review = db.session.execute(
            db.select(Review).where(Review.course_id == course_id, Review.user_id == current_user.id)
        ).scalar()

    return render_template('courses/show.html', course=course, reviews=reviews, user_review=user_review)


@bp.route('/<int:course_id>/reviews')
def reviews(course_id):
    course = db.get_or_404(Course, course_id)
    sort = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)

    query = db.select(Review).where(Review.course_id == course_id)


    if sort == 'newest':
        query = query.order_by(Review.created_at.desc())
    elif sort == 'positive':
        query = query.order_by(Review.rating.desc(), Review.created_at.desc())
    elif sort == 'negative':
        query = query.order_by(Review.rating.asc(), Review.created_at.desc())


    pagination = db.paginate(query, page=page, per_page=REVIEWS_PER_PAGE, error_out=False)
    reviews_list = pagination.items

    user_review = None
    if current_user.is_authenticated:
        user_review = db.session.execute(
            db.select(Review).where(Review.course_id == course_id, Review.user_id == current_user.id)
        ).scalar()

    return render_template('courses/reviews.html',
                           course=course,
                           pagination=pagination,
                           reviews=reviews_list,
                           sort=sort,
                           user_review=user_review)


@bp.route('/<int:course_id>/reviews/add', methods=['POST'])
@login_required
def add_review(course_id):
    course = db.get_or_404(Course, course_id)


    existing_review = db.session.execute(
        db.select(Review).where(Review.course_id == course_id, Review.user_id == current_user.id)
    ).scalar()

    if existing_review:
        flash('Вы уже оставили отзыв на этот курс.', 'warning')
        return redirect(url_for('courses.show', course_id=course_id))

    rating = request.form.get('rating', type=int)
    text = request.form.get('text', '').strip()

    if rating is None or rating < 0 or rating > 5 or not text:
        flash('Заполните все поля корректно.', 'danger')
        return redirect(url_for('courses.show', course_id=course_id))

    review = Review(rating=rating, text=text, course_id=course_id, user_id=current_user.id)

    try:
        db.session.add(review)
        course.reviews.append(review)
        course.update_rating()
        db.session.commit()
        flash('Ваш отзыв успешно добавлен!', 'success')
    except Exception:
        db.session.rollback()
        flash('Ошибка добавления отзыва.', 'danger')

    return redirect(url_for('courses.show', course_id=course_id))