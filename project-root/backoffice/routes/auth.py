import bcrypt

# Créer le hash (au moment de créer un user)
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Vérifier le mot de passe (au moment du login)
bcrypt.checkpw(entered_password.encode(), user.password_hash)