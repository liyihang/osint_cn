class Config:
    def __init__(self):
        self.debug = True
        self.secret_key = 'your_secret_key'

class DatabaseConfig:
    def __init__(self):
        self.host = 'localhost'
        self.port = 5432
        self.user = 'your_user'
        self.password = 'your_password'
        self.database = 'your_database'