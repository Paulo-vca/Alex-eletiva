import logging
import tempfile
from flask import send_file
import sqlalchemy as sqla
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import (FileField, IntegerField, StringField, SubmitField,
                     TextAreaField)
from wtforms.validators import DataRequired

meu_app = Flask(__name__)
meu_app.secret_key = 'sua_chave_secreta'


engine = sqla.create_engine('sqlite:///bliotech.sqlite', echo=True, poolclass=sqla.StaticPool)

connection = engine.connect()

metadata_db = sqla.MetaData()

user = sqla.Table(
   'user', metadata_db,
   sqla.Column('id', sqla.Integer, primary_key=True, autoincrement=True),
   sqla.Column('username', sqla.String),
   sqla.Column('email', sqla.String),
   sqla.Column('password', sqla.String)
)

livro = sqla.Table(
   'livro', metadata_db,
   sqla.Column('id', sqla.Integer, primary_key=True, autoincrement=True),
   sqla.Column('titulo', sqla.String),
   sqla.Column('autor', sqla.String),
   sqla.Column('ano_publicacao', sqla.String), 
   sqla.Column('descricao', sqla.String),  
   sqla.Column('arquivo_pdf', sqla.LargeBinary),  
)

livrosfavoritos = sqla.Table(
   'livrosfavoritos', metadata_db,
   sqla.Column('id', sqla.Integer, primary_key=True, autoincrement=True),
   sqla.Column('user_id', sqla.Integer),
   sqla.Column('livro_id', sqla.Integer)
)

class LivroForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired()])
    autor = StringField('Autor', validators=[DataRequired()])
    ano_publicacao = StringField('Ano de Publicação', validators=[DataRequired()])
    descricao = TextAreaField('Descrição', validators=[DataRequired()])
    arquivo_pdf = FileField('Arquivo PDF', validators=[FileAllowed(['pdf'], 'Apenas arquivos PDF permitidos!')])
    submit = SubmitField('Cadastrar Livro')

@meu_app.route('/cadastrarLivros', methods=['GET', 'POST'])
def cadastrar_livro():
    form = LivroForm()

    if form.validate_on_submit():
        # Obtém os dados do formulário
        titulo = form.titulo.data
        autor = form.autor.data
        ano_publicacao = form.ano_publicacao.data
        descricao = form.descricao.data
        arquivo_pdf = form.arquivo_pdf.data.read()

        # Insere os dados na tabela livro
        novo_livro = sqla.insert(livro).values(
            titulo=titulo,
            autor=autor,
            ano_publicacao=ano_publicacao,
            descricao=descricao,
            arquivo_pdf=arquivo_pdf
        )
        connection.execute(novo_livro)

        flash('Livro cadastrado com sucesso!')
        return redirect(url_for('index'))

    return render_template('cadastrarLivros.html', form=form)


@meu_app.route('/')
def index():
    # Consulta os livros no banco de dados
    query = sqla.select(livro)
    result = connection.execute(query).fetchall()

    # Renderiza a página com a lista de livros
    return render_template('index.html', livros=result)

@meu_app.route('/atualizar_livro/<livro_id>', methods=['GET', 'POST'])
def atualizar_livro(livro_id):
    # Recupera os dados do livro pelo ID
    query = sqla.select(livro).where(livro.c.id == livro_id)
    livro_atualizar = connection.execute(query).fetchone()

    form = LivroForm(obj=livro_atualizar)

    if form.validate_on_submit():
        # Atualiza os dados do livro no banco
        query = sqla.update(livro).where(livro.c.id == livro_id).values(
            titulo=form.titulo.data,
            autor=form.autor.data,
            ano_publicacao=form.ano_publicacao.data,
            descricao=form.descricao.data
        )
        connection.execute(query)

        flash('Livro atualizado com sucesso!')
        return redirect(url_for('index'))

    return render_template('atualizarLivro.html', form=form)

@meu_app.route('/deletar_livro/<livro_id>', methods=['POST'])
def deletar_livro(livro_id):
    # Exclui o livro do banco
    query = sqla.delete(livro).where(livro.c.id == livro_id)
    connection.execute(query)

    flash('Livro excluído com sucesso!')
    return redirect(url_for('index'))


@meu_app.route('/ver_pdf/<livro_id>')
def ver_pdf(livro_id):
    # Recupera os dados do livro pelo ID
    query = sqla.select(livro).where(livro.c.id == livro_id)
    livro_pdf = connection.execute(query).fetchone()

    if livro_pdf and livro_pdf['arquivo_pdf']:
        # Cria um arquivo temporário para exibir o PDF
        with tempfile.NamedTemporaryFile(delete=False) as tmp_pdf:
            tmp_pdf.write(livro_pdf['arquivo_pdf'])
            tmp_pdf_path = tmp_pdf.name

        # Retorna o arquivo PDF para ser exibido no navegador
        return send_file(tmp_pdf_path, as_attachment=False, attachment_filename='livro.pdf')

    flash('Nenhum arquivo PDF disponível para este livro.')
    return redirect(url_for('index'))

@meu_app.route('/pesquisar_livros', methods=['GET'])
def pesquisar_livros():
    # Obtém o termo de pesquisa da query string
    query = request.args.get('query', '')

    # Realiza a pesquisa no banco de dados
    query_pesquisa = livro.select().where(
        livro.c.titulo.ilike(f"%{query}%") |
        livro.c.autor.ilike(f"%{query}%") |
        livro.c.descricao.ilike(f"%{query}%")
    )
    resultados_pesquisa = connection.execute(query_pesquisa).fetchall()

    return render_template('pesquisaLivros.html', livros=resultados_pesquisa, query=query)



@meu_app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        novo_usuario = sqla.insert(user).values(username=username, email=email, password=password)
        connection.execute(novo_usuario)

        logging.debug(f"Novo usuário cadastrado: {username}, {email}")


        return redirect(url_for('login'))

    return render_template('cadastrar.html')

@meu_app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'usuario' and password == 'senha':
            return redirect(url_for('perfil', username=username))  
        else:
            pass

    return render_template('login.html')

@meu_app.route('/perfil/<username>')
def perfil(username):
    user_details = {'username': username, 'email': 'usuario@example.com'}  

    return render_template('perfil.html', user_details=user_details)

# @meu_app.route('/')
# def index():
#     return render_template('index.html')

if __name__ == '__main__':
    meu_app.run(debug=True)
    # Criação das tabelas
    metadata_db.create_all(engine)
