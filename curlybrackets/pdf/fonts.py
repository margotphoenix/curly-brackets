

from reportlab.pdfbase.pdfmetrics import registerFont, registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont, TTFError


# BASE_FONT = 'Helvetica'

try:
    registerFont(TTFont('ZenKakuGothicAntique', 'ZenKakuGothicAntique-Regular.ttf'))
    registerFont(TTFont('ZenKakuGothicAntique-Bold', 'ZenKakuGothicAntique-Bold.ttf'))
    registerFontFamily('ZenKakuGothicAntique', 
                       normal='ZenKakuGothicAntique', 
                       bold='ZenKakuGothicAntique-Bold')
except TTFError:
    BASE_FONT = 'Helvetica'
    # DEFAULT_FONT = BASE_FONT
else:
    BASE_FONT = 'ZenKakuGothicAntique'

try:
    registerFont(TTFont('NotoSansCJKtc', 'NotoSansCJKtc-VF.ttf'))
    registerFont(TTFont('ArialUnicode', 'Arial Unicode.ttf'))
# except TTFError:
#     pass
except TTFError:
    DEFAULT_FONT = BASE_FONT
else:
    DEFAULT_FONT = 'NotoSansCJKtc'
    # DEFAULT_FONT = 'ArialUnicode'
