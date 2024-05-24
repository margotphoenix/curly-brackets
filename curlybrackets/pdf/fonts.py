

from reportlab.pdfbase.pdfmetrics import registerFont, registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont, TTFError


BASE_FONT = 'Helvetica'

try:
    registerFont(TTFont('UnGraphic', 'UnGraphic.ttf'))
    registerFont(TTFont('UnGraphic-Bold', 'UnGraphicBold.ttf'))
    registerFontFamily('UnGraphic', 
                       normal='UnGraphic', 
                       bold='UnGraphic-Bold')
except TTFError:
    DEFAULT_FONT = BASE_FONT
else:
    DEFAULT_FONT = 'UnGraphic'

try:
    registerFont(TTFont('PretendardJP-Regular', 'PretendardJP-Regular.ttf'))
    registerFont(TTFont('PretendardJP-Bold', 'PretendardJP-Bold.ttf'))
    registerFontFamily('PretendardJP', 
                       normal='PretendardJP-Regular', 
                       bold='PretendardJP-Bold')
except TTFError:
    pass
