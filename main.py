from flask import Flask, render_template, redirect, abort, request, make_response, jsonify
from data import db_session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_restful import reqparse, abort, Api, Resource
from forms import RegisterForm, LoginForm, BooksForm, AuthorForm, InputForm
from data.users import User
from data.books import Books
from data.author import Author
from data.users_recource import UsersListResource, UsersResource
from data.books_resource import BooksResource, BooksListResource
from data.author_resource import AuthorsResource, AuthorsListResource
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'WEB_SERVER_project'
login_manager = LoginManager()
login_manager.init_app(app)
api = Api(app)


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id)


# Главная: обдумать, что будет!
@app.route('/', methods=['GET', 'POST'])
@app.route('/main', methods=['GET', 'POST'])
def index():
    form = InputForm()
    if form.validate_on_submit():
        message = form.message.data
        answer = request.form['req']
        return sent(message, answer)
    return render_template("main.html", title='Главная', form=form, warning='')


@login_required
def sent(message, answer):
    answers = ['Вывод пользователей (введите users)', 'Книга(введите название)', 'Автор(введите имя и фамилию)']
    a = answers.index(answer)
    print(message, answer)
    form = InputForm()
    if a == 0:
        if current_user.id == 1:
            return redirect('/api/v1/users')
        else:
            return render_template("main.html", title='Главная', form=form, warning='Недостаточно прав')
    elif a == 1:
        session = db_session.create_session()
        names, surnames = [], []
        book = session.query(Books).filter(Books.title == message).first()
        author = session.query(Author).filter(Author.id == book.author_id).first()
        names.append(author.name)
        surnames.append(author.surname)
        return render_template('books.html', books=[book], names=names, surnames=surnames)
    elif a == 2:
        session = db_session.create_session()
        name, surname = message.split()
        author = session.query(Author).filter(Author.name == name, Author.surname == surname).first()
        return render_template('authors.html', authors=[author])


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/api/v1/users')
@login_required
def users():
    session = db_session.create_session()
    users = session.query(User).all()
    return render_template('users.html', users=users)



# Страница регистрации
@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            surname=form.surname.data,
            nickname=form.nickname.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/login')
        # return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)


# Страница авторизации
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


# Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


# Отображение всех писателей
@app.route('/authors')
def authors():
    session = db_session.create_session()
    author = session.query(Author).all()
    return render_template('authors.html', authors=author)


# Добавление писателя (только админ)
@app.route('/addauthor', methods=['GET', 'POST'])
@login_required
def addauthor():
    form = AuthorForm()
    session = db_session.create_session()
    if form.validate_on_submit():
        if session:
            author = Author(
            name=form.name.data,
            surname=form.surname.data,
            years=form.years.data,
            list_of_books=form.list_of_books.data
            )
            session.add(author)
            session.commit()
            return redirect("/")
        return redirect('/logout')
    return render_template('addauthor.html', title='Добавление писателя', form=form)


@app.route('/author_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def author_delete(id):
    session = db_session.create_session()
    author = session.query(Author).filter(Author.id == id,
                                   current_user.id == 1).first()
    if author:
        session.delete(author)
        session.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/authors/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_authors(id):
    form = AuthorForm()
    if request.method == "GET":
        session = db_session.create_session()
        author = session.query(Author).filter(Author.id == id,
                                          current_user.id == 1).first()
        if author:
            form.name.data = author.name
            form.surname.data = author.surname
            form.years.data = author.years
            form.list_of_books.data = author.list_of_books
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        author = session.query(Author).filter(Author.id == id,
                                              current_user.id == 1).first()
        if author:
            author.name = form.name.data
            author.surname = form.surname.data
            author.years = form.years.data
            author.list_of_books = form.list_of_books.data
            session.commit()
            return redirect('/authors')
        else:
            abort(404)
    return render_template('addauthor.html', title='Редактирование авторов', form=form)

# Отображение всех книг
@app.route('/books')
def books():
    session = db_session.create_session()
    books = session.query(Books).all()
    names, surnames = [], []
    for book in session.query(Books).all():
        author = session.query(Author).filter(Author.id == book.author_id).first()
        names.append(author.name)
        surnames.append(author.surname)
    print(names)
    return render_template('books.html', books=books, names=names, surnames=surnames)


@app.route('/books_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def books_delete(id):
    session = db_session.create_session()
    books = session.query(Books).filter(Books.id == id,
                                   current_user.id == 1).first()
    if books:
        session.delete(books)
        session.commit()
        os.remove(f'static/img/book{books.id}.jpg')
    else:
        abort(404)
    return redirect('/')


# Добавление книги (только админ)
@app.route('/addbooks', methods=['GET', 'POST'])
@login_required
def addbooks():
    form = BooksForm()
    session = db_session.create_session()
    author = session.query(Author)
    if form.validate_on_submit():
        if session:
            book = Books(
            author_id=author.filter(Author.surname == form.author.data).first().id,
            title=form.title.data,
            date=form.date.data,
            price=form.price.data
            )
            book.cover = 'string'  # заглушка
            # Идея: создаю новую книгу, но заранее мне неизвестен ее id для корректного названия книги
            session.add(book)
            session.commit()
            book = session.query(Books).filter(Books.title == form.title.data).first()
            photo = f"book{book.id}.jpg"
            f = request.files['file']
            with open(photo, "wb") as file:
                file.write(f.read())
            book.cover = photo
            session.commit()
            return redirect("/")
        return redirect('/logout')
    return render_template('addbooks.html', title='Добавление книги', form=form)


@app.route('/books/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_book(id):
    form = BooksForm()
    if request.method == "GET":
        session = db_session.create_session()
        book = session.query(Books).filter(Books.id == id,
                                          current_user.id == 1).first()
        if book:
            author = session.query(Author).filter(Author.id == book.author_id).first()
            form.author.data = author.surname
            form.title.data = book.title
            form.date.data = book.date
            form.cover.data = book.cover
            form.price.data = book.price
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        book = session.query(Books).filter(Books.id == id,
                                           current_user.id == 1).first()
        if book:
            author = session.query(Author).filter(Author.surname == form.author.data).first()
            book.author_id = author.id
            book.title = form.title.data
            book.date = form.date.data
            book.price = form.price.data
            book.cover = form.cover.data
            session.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('addbooks.html', title='Редактирование книги', form=form)


# Запуск программы
def main():
    db_session.global_init("db/book_shop.sqlite")
    api.add_resource(UsersListResource, '/api/v1/users')
    api.add_resource(UsersResource, '/api/v1/users/<int:user_id>')
    api.add_resource(BooksListResource, '/api/v1/books')
    api.add_resource(BooksResource, '/api/v1/books/<int:books_id>')
    api.add_resource(AuthorsListResource, '/api/v1/author')
    api.add_resource(AuthorsResource, '/api/v1/books/<int:author_id>')
    app.run()


if __name__ == '__main__':
    main()
