

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
    pass 

try:
    registerFont(TTFont('ZenKakuGothicAntique', 'ZenKakuGothicAntique-Regular.ttf'))
    registerFont(TTFont('ZenKakuGothicAntique-Bold', 'ZenKakuGothicAntique-Bold.ttf'))
    registerFontFamily('ZenKakuGothicAntique', 
                       normal='ZenKakuGothicAntique', 
                       bold='ZenKakuGothicAntique-Bold')
    # registerFont(TTFont('Mplus1', 'Mplus1-Regular.ttf'))
    # registerFont(TTFont('Mplus1-Bold', 'Mplus1-Bold.ttf'))
    # registerFontFamily('Mplus1', 
    #                    normal='Mplus1', 
    #                    bold='Mplus1-Bold')
    # registerFont(TTFont('PretendardJP', 'PretendardJP-Regular.ttf'))
    # registerFont(TTFont('PretendardJP-Bold', 'PretendardJP-Bold.ttf'))
    # registerFontFamily('PretendardJP', 
    #                    normal='PretendardJP', 
    #                    bold='PretendardJP-Bold')
except TTFError:
    DEFAULT_FONT = BASE_FONT
else:
    DEFAULT_FONT = 'ZenKakuGothicAntique'
    # DEFAULT_FONT = 'PretendardJP'
