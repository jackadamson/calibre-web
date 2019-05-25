from flask import Blueprint, render_template, abort

books_template = Blueprint(
    'books_template',
    __name__,
    template_folder='templates'
)

