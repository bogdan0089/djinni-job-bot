class UserNotFoundError(Exception):
    def __init__(self, telegram_id: int):
        super().__init__(f"User {telegram_id} not found.")

class UsersNotFoundError(Exception):
    def __init__(self):
        super().__init__(f"User not found.")