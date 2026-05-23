from app import app
from models import db, User


def create_multiple_users():
    with app.app_context():

        users = [
            {'login': 'user1', 'password': 'pass1', 'first_name': 'User', 'last_name': 'One'},
            {'login': 'user2', 'password': 'pass2', 'first_name': 'User', 'last_name': 'Two'},
            {'login': 'admin', 'password': 'admin123', 'first_name': 'Admin', 'last_name': 'Adminov'},
        ]

        for u_data in users:

            existing = db.session.execute(
                db.select(User).filter_by(login=u_data['login'])
            ).scalar_one_or_none()

            if existing:
                print(f"Пользователь {u_data['login']} уже существует, удаляем старого...")
                db.session.delete(existing)
                db.session.commit()


            user = User(
                first_name=u_data['first_name'],
                last_name=u_data['last_name'],
                login=u_data['login']
            )
            user.set_password(u_data['password'])
            db.session.add(user)
            print(f"Создан пользователь: {u_data['login']} с паролем {u_data['password']}")

        db.session.commit()


        print("\n--- Список всех пользователей ---")
        all_users = db.session.execute(db.select(User)).scalars().all()
        for u in all_users:
            print(f"Логин: {u.login}, Имя: {u.full_name}")


if __name__ == '__main__':
    create_multiple_users()