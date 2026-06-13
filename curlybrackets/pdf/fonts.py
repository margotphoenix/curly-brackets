

from reportlab.pdfbase.pdfmetrics import registerFont, registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont, TTFError


BASE_FONT = 'Arial'

try:
    registerFont(TTFont('UnGraphic', 'UnGraphic.ttf'))
    registerFont(TTFont('UnGraphic-Bold', 'UnGraphicBold.ttf'))
    registerFontFamily('UnGraphic', 
                       normal='UnGraphic', 
                       bold='UnGraphic-Bold')
except TTFError:
    pass
# except TTFError:
#     DEFAULT_FONT = BASE_FONT
# else:
#     DEFAULT_FONT = 'UnGraphic'

try:
    # registerFont(TTFont('ZenKakuGothicAntique', 'ZenKakuGothicAntique-Regular.ttf'))
    # registerFont(TTFont('ZenKakuGothicAntique-Bold', 'ZenKakuGothicAntique-Bold.ttf'))
    # registerFontFamily('ZenKakuGothicAntique', 
    #                    normal='ZenKakuGothicAntique', 
    #                    bold='ZenKakuGothicAntique-Bold')
    # registerFont(TTFont('Mplus1', 'Mplus1-Regular.ttf'))
    # registerFont(TTFont('Mplus1-Bold', 'Mplus1-Bold.ttf'))
    # registerFontFamily('Mplus1', 
    #                    normal='Mplus1', 
    #                    bold='Mplus1-Bold')
    # registerFont(TTFont('PretendardJP-Regular', 'PretendardJP-Regular.ttf'))
    # registerFont(TTFont('PretendardJP-Bold', 'PretendardJP-Bold.ttf'))
    # registerFontFamily('PretendardJP', 
    #                    normal='PretendardJP-Regular', 
    #                    bold='PretendardJP-Bold')
    # registerFont(TTFont('NotoSansCJKtc', 'NotoSansCJKtc-VF.ttf'))
    registerFont(TTFont('ArialUnicode', 'Arial Unicode.ttf'))
# except TTFError:
#     pass
except TTFError:
    DEFAULT_FONT = BASE_FONT
else:
    # DEFAULT_FONT = 'ZenKakuGothicAntique'
    # DEFAULT_FONT = 'Mplus1'
    # DEFAULT_FONT = 'PretendardJP'
    # DEFAULT_FONT = 'NotoSansCJKtc'
    DEFAULT_FONT = 'ArialUnicode'