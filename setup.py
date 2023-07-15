from distutils.core import setup

setup(name="curly-brackets",
      author="Margot Wasserman",
      author_email="margotphxw@gmail.com",
      version="0.5.0",  # New start on github
      url="https://github.com/margotphoenix/curly-brackets",
      description="Tools for tournaments",
      packages=['curlybrackets'],
      # package_dir={'': 'src'},
      package_data={'curlybrackets': ['pdf/templates/*.pdf',
                                      'pdf/templates/config.json']},
      install_requires=['python-dateutil', 'pytz', 'reportlab', 'PyPDF2',
                        'pandas', 'pychallonge', 'requests'])
