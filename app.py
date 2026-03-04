import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # Para manejar nombres de archivos seguros
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mi_clave_secreta_super_segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///red_social.db'

# --- CONFIGURACIÓN DE SUBIDA DE IMÁGENES ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Crear la carpeta de uploads si no existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='author', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(100), nullable=True) # Nombre del archivo de imagen
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- RUTAS ---

@app.route('/')
@login_required
def index():
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        is_admin = True if User.query.count() == 0 else False
        
        # Corregido: sin el parámetro method='sha256'
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw, is_admin=is_admin)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Cuenta creada. ¡Ya puedes iniciar sesión!')
            return redirect(url_for('login'))
        except:
            flash('El nombre de usuario ya existe.')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash('Inicio de sesión fallido.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')
    file = request.files.get('image') # Obtener archivo del formulario
    filename = None

    # Si hay un archivo y es válido
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Añadir timestamp al nombre para evitar duplicados
        filename = f"{datetime.now().timestamp()}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    if content or filename:
        new_post = Post(content=content, author=current_user, image=filename)
        db.session.add(new_post)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author == current_user or current_user.is_admin:
        # Borrar el archivo físico si existe
        if post.image:
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image)
            if os.path.exists(img_path):
                os.remove(img_path)
        
        db.session.delete(post)
        db.session.commit()
        flash('Publicación eliminada.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)