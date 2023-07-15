

from reportlab.pdfbase.pdfmetrics import registerFont, registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont, TTFError


BASE_FONT = 'Helvetica'
try:
    registerFont(TTFont('UnGraphic', 'UnGraphic.ttf'))
    registerFont(TTFont('UnGraphicBold', 'UnGraphicBold.ttf'))
    registerFontFamily('UnGraphic', normal='UnGraphic', bold='UnGraphicBold')
except TTFError:
    DEFAULT_FONT = BASE_FONT
else:
    DEFAULT_FONT = 'UnGraphic'
