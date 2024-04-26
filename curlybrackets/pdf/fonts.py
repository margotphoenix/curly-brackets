

from reportlab.pdfbase.pdfmetrics import registerFont, registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont, TTFError


BASE_FONT = 'Helvetica'

try:
    registerFont(TTFont('UnGraphic', 'UnGraphic.ttf'))
    registerFont(TTFont('UnGraphicBold', 'UnGraphicBold.ttf'))
    registerFontFamily('UnGraphic', 
                       normal='UnGraphic', 
                       bold='UnGraphicBold')
except TTFError:
    pass 

try:
    registerFont(TTFont('PretendardJP', 'PretendardJP-Regular.ttf'))
    registerFont(TTFont('PretendardJP-Bold', 'PretendardJP-Bold.ttf'))
    registerFontFamily('PretendardJP', 
                       normal='PretendardJP', 
                       bold='PretendardJP-Bold')
except TTFError:
    DEFAULT_FONT = BASE_FONT
else:
    DEFAULT_FONT = 'PretendardJP'
