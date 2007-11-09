r"""

OVERVIEW

  mathtext is a module for parsing TeX expressions and drawing them
  into a matplotlib.ft2font image buffer.  You can draw from this
  buffer into your backend.

  A large set of the TeX symbols are provided (see below).
  Subscripting and superscripting are supported, as well as the
  over/under style of subscripting with \sum, \int, etc.

  The module uses pyparsing to parse the TeX expression, an so can
  handle fairly complex TeX expressions Eg, the following renders
  correctly

  s = r'$\mathcal{R}\prod_{i=\alpha\mathcal{B}}^\infty a_i\sin(2 \pi f x_i)$'

  The fonts \cal, \rm, \it, and \tt are allowed.

  The following accents are provided: \hat, \breve, \grave, \bar,
  \acute, \tilde, \vec, \dot, \ddot.  All of them have the same
  syntax, eg to make an overbar you do \bar{o} or to make an o umlaut
  you do \ddot{o}.  The shortcuts are also provided, eg: \"o \'e \`e
  \~n \.x \^y

  The spacing elements \ , \/ and \hspace{num} are provided.  \/
  inserts a small space, and \hspace{num} inserts a fraction of the
  current fontsize.  Eg, if num=0.5 and the fontsize is 12.0,
  hspace{0.5} inserts 6 points of space



  If you find TeX expressions that don't parse or render properly,
  please email me, but please check KNOWN ISSUES below first.

REQUIREMENTS

  mathtext requires matplotlib.ft2font.  Set BUILD_FT2FONT=True in
  setup.py.  See BACKENDS below for a summary of availability by
  backend.

LICENSING:

  The computer modern fonts this package uses are part of the BaKoMa
  fonts, which are (now) free for commercial and noncommercial use and
  redistribution; see license/LICENSE_BAKOMA in the matplotlib src
  distribution for redistribution requirements.

USAGE:

  See http://matplotlib.sourceforge.net/tutorial.html#mathtext for a
  tutorial introduction.

  Any text element (xlabel, ylabel, title, text, etc) can use TeX
  markup, as in

    xlabel(r'$\Delta_i$')
           ^
        use raw strings

  Math and non-math can be interpresed in the same string.  E.g.,

    r'My label $x_i$'.

  A large set of the TeX symbols are provided.  Subscripting and
  superscripting are supported, as well as the over/under style of
  subscripting with \sum, \int, etc.


  Allowed TeX symbols:

  [MGDTODO: This list is no longer exhaustive and needs to be updated]

  \/ \Delta \Downarrow \Gamma \Im \LEFTangle \LEFTbrace \LEFTbracket
  \LEFTparen \Lambda \Leftarrow \Leftbrace \Leftbracket \Leftparen
  \Leftrightarrow \Omega \P \Phi \Pi \Psi \RIGHTangle \RIGHTbrace
  \RIGHTbracket \RIGHTparen \Re \Rightarrow \Rightbrace \Rightbracket
  \Rightparen \S \SQRT \Sigma \Sqrt \Theta \Uparrow \Updownarrow
  \Upsilon \Vert \Xi \aleph \alpha \approx \angstrom \ast \asymp
  \backslash \beta \bigcap \bigcirc \bigcup \bigodot \bigoplus
  \bigotimes \bigtriangledown \bigtriangleup \biguplus \bigvee
  \bigwedge \bot \bullet \cap \cdot \chi \circ \clubsuit \coprod \cup
  \dag \dashv \ddag \delta \diamond \diamondsuit \div \downarrow \ell
  \emptyset \epsilon \equiv \eta \exists \flat \forall \frown \gamma
  \geq \gg \heartsuit \hspace \imath \in \infty \int \iota \jmath
  \kappa \lambda \langle \lbrace \lceil \leftangle \leftarrow
  \leftbrace \leftbracket \leftharpoondown \leftharpoonup \leftparen
  \leftrightarrow \leq \lfloor \ll \mid \mp \mu \nabla \natural
  \nearrow \neg \ni \nu \nwarrow \odot \oint \omega \ominus \oplus
  \oslash \otimes \phi \pi \pm \prec \preceq \prime \prod \propto \psi
  \rangle \rbrace \rceil \rfloor \rho \rightangle \rightarrow
  \rightbrace \rightbracket \rightharpoondown \rightharpoonup
  \rightparen \searrow \sharp \sigma \sim \simeq \slash \smile
  \spadesuit \sqcap \sqcup \sqrt \sqsubseteq \sqsupseteq \subset
  \subseteq \succ \succeq \sum \supset \supseteq \swarrow \tau \theta
  \times \top \triangleleft \triangleright \uparrow \updownarrow
  \uplus \upsilon \varepsilon \varphi \varphi \varrho \varsigma
  \vartheta \vdash \vee \vert \wedge \wp \wr \xi \zeta


BACKENDS

  mathtext currently works with GTK, Agg, GTKAgg, TkAgg and WxAgg and
  PS, though only horizontal and vertical rotations are supported in
  *Agg

  mathtext now embeds the TrueType computer modern fonts into the PS
  file, so what you see on the screen should be what you get on paper.

  Backends which don't support mathtext will just render the TeX
  string as a literal.  Stay tuned.


KNOWN ISSUES:

  - Certainly there are some...

Author    : John Hunter <jdhunter@ace.bsd.uchicago.edu>
            Michael Droettboom <mdroe@stsci.edu>
               (rewrite based on TeX box layout algorithms)
Copyright : John Hunter (2004,2005)
License   : matplotlib license (PSF compatible)

"""
from __future__ import division
import os, sys
from cStringIO import StringIO
from math import floor, ceil
from sets import Set
import unicodedata
from warnings import warn

from numpy import inf, isinf

from matplotlib import verbose
from matplotlib.pyparsing import Literal, Word, OneOrMore, ZeroOrMore, Combine, Group, \
     Optional, Forward, NotAny, alphas, nums, alphanums, StringStart, \
     StringEnd, ParseFatalException, FollowedBy, Regex, operatorPrecedence, \
     opAssoc, ParseResults, Or, Suppress, oneOf, ParseException, MatchFirst, \
     NoMatch, Empty

from matplotlib.afm import AFM
from matplotlib.cbook import enumerate, iterable, Bunch, get_realpath_and_stat, \
    is_string_like
from matplotlib.ft2font import FT2Font, FT2Image, KERNING_DEFAULT, LOAD_FORCE_AUTOHINT, LOAD_NO_HINTING
from matplotlib.font_manager import findfont, FontProperties
from matplotlib._mathtext_data import latex_to_bakoma, \
        latex_to_standard, tex2uni, type12uni, tex2type1, uni2type1, \
        latex_to_cmex
from matplotlib import get_data_path, rcParams

####################



##############################################################################
# FONTS

def get_unicode_index(symbol):
    """get_unicode_index(symbol) -> integer

Return the integer index (from the Unicode table) of symbol.
symbol can be a single unicode character, a TeX command (i.e. r'\pi'),
or a Type1 symbol name (i.e. 'phi').

"""
    # From UTF #25: U+2212 minus sign is the preferred
    # representation of the unary and binary minus sign rather than
    # the ASCII-derived U+002D hyphen-minus, because minus sign is
    # unambiguous and because it is rendered with a more desirable
    # length, usually longer than a hyphen.
    if symbol == '-':
        return 0x2212
    try:# This will succeed if symbol is a single unicode char
        return ord(symbol)
    except TypeError:
        pass
    try:# Is symbol a TeX symbol (i.e. \alpha)
        return tex2uni[symbol.strip("\\")]
    except KeyError:
        message = """'%(symbol)s' is not a valid Unicode character or
TeX/Type1 symbol"""%locals()
        raise ValueError, message


#Not used, but might turn useful
def get_type1_name(symbol):
    """get_type1_name(symbol) -> string

Returns the the Type1 name of symbol.
symbol can be a single unicode character, or a TeX command (i.e. r'\pi').

"""
    try:# This will succeed if symbol is a single unicode char
        return uni2type1[ord(symbol)]
    except TypeError:
        pass
    try:# Is symbol a TeX symbol (i.e. \alpha)
        return tex2type1[symbol.strip("\\")]
    except KeyError:
        pass
    # The symbol is already a Type1 name so return it
    if isinstance(symbol, str):
        return symbol
    else:
        # The user did not suply a valid symbol, show usage
        raise ValueError, get_type1_name.__doc__

class MathtextBackend(object):
    def __init__(self):
        self.fonts_object = None

    def set_canvas_size(self, w, h, d):
        'Dimension the drawing canvas; may be a noop'
        self.width  = w
        self.height = h
        self.depth  = d

    def render_glyph(self, ox, oy, info):
        raise NotImplementedError()

    def render_filled_rect(self, x1, y1, x2, y2):
        raise NotImplementedError()

    def get_results(self, box):
        """Return a backend specific tuple of things to return to the
        backend after all processing is done."""
        raise NotImplementedError()

    def get_hinting_type(self):
        return LOAD_NO_HINTING

class MathtextBackendBbox(MathtextBackend):
    """A backend whose only purpose is to get a precise bounding box.
    Only required for the Agg backend."""
    
    def __init__(self, real_backend):
        MathtextBackend.__init__(self)
        self.bbox = [0, 0, 0, 0]
        self.real_backend = real_backend

    def _update_bbox(self, x1, y1, x2, y2):
        self.bbox = [min(self.bbox[0], x1),
                     min(self.bbox[1], y1),
                     max(self.bbox[2], x2),
                     max(self.bbox[3], y2)]
        
    def render_glyph(self, ox, oy, info):
        self._update_bbox(ox + info.metrics.xmin,
                          oy - info.metrics.ymax,
                          ox + info.metrics.xmax,
                          oy - info.metrics.ymin)

    def render_rect_filled(self, x1, y1, x2, y2):
        self._update_bbox(x1, y1, x2, y2)

    def get_results(self, box):
        orig_height = box.height
        orig_depth  = box.depth
        ship(0, 0, box)
        bbox = self.bbox
        bbox = [bbox[0] - 1, bbox[1] - 1, bbox[2] + 1, bbox[3] + 1]
        self._switch_to_real_backend()
        self.fonts_object.set_canvas_size(
            bbox[2] - bbox[0],
            (bbox[3] - bbox[1]) - orig_depth,
            (bbox[3] - bbox[1]) - orig_height)
        ship(-bbox[0], -bbox[1], box)
        return self.fonts_object.get_results(box)

    def get_hinting_type(self):
        return self.real_backend.get_hinting_type()

    def _switch_to_real_backend(self):
        self.fonts_object.mathtext_backend = self.real_backend
        self.real_backend.fonts_object = self.fonts_object
        self.real_backend.ox = self.bbox[0]
        self.real_backend.oy = self.bbox[1]
        
class MathtextBackendAggRender(MathtextBackend):
    def __init__(self):
        self.ox = 0
        self.oy = 0
        self.image = None
        MathtextBackend.__init__(self)
    
    def set_canvas_size(self, w, h, d):
        MathtextBackend.set_canvas_size(self, w, h, d)
        self.image = FT2Image(ceil(w), ceil(h + d))

    def render_glyph(self, ox, oy, info):
        info.font.draw_glyph_to_bitmap(
            self.image, ox, oy - info.metrics.ymax, info.glyph)

    def render_rect_filled(self, x1, y1, x2, y2):
        self.image.draw_rect_filled(x1, y1, x2, max(y2 - 1, y1))

    def get_results(self, box):
        return (self.ox,
                self.oy,
                self.width,
                self.height + self.depth,
                self.depth,
                self.image,
                self.fonts_object.get_used_characters())

    def get_hinting_type(self):
        return LOAD_FORCE_AUTOHINT

def MathtextBackendAgg():
    return MathtextBackendBbox(MathtextBackendAggRender())
    
class MathtextBackendBitmapRender(MathtextBackendAggRender):
    def get_results(self, box):
        return self.image
    
def MathtextBackendBitmap():
    return MathtextBackendBbox(MathtextBackendBitmapRender())

class MathtextBackendPs(MathtextBackend):
    def __init__(self):
        self.pswriter = StringIO()
        self.lastfont = None

    def render_glyph(self, ox, oy, info):
        oy = self.height - oy + info.offset
        postscript_name = info.postscript_name
        fontsize        = info.fontsize
        symbol_name     = info.symbol_name

        if (postscript_name, fontsize) != self.lastfont:
            ps = """/%(postscript_name)s findfont
%(fontsize)s scalefont
setfont
""" % locals()
            self.lastfont = postscript_name, fontsize
            self.pswriter.write(ps)
        
        ps = """%(ox)f %(oy)f moveto
/%(symbol_name)s glyphshow\n
""" % locals()
        self.pswriter.write(ps)

    def render_rect_filled(self, x1, y1, x2, y2):
        ps = "%f %f %f %f rectfill\n" % (x1, self.height - y2, x2 - x1, y2 - y1)
        self.pswriter.write(ps)

    def get_results(self, box):
        ship(0, -self.depth, box)
        #print self.depth
        return (self.width,
                self.height + self.depth,
                self.depth,
                self.pswriter,
                self.fonts_object.get_used_characters())

class MathtextBackendPdf(MathtextBackend):
    def __init__(self):
        self.glyphs = []
        self.rects = []

    def render_glyph(self, ox, oy, info):
        filename = info.font.fname
        oy = self.height - oy + info.offset
        self.glyphs.append(
            (ox, oy, filename, info.fontsize,
             info.num, info.symbol_name))

    def render_rect_filled(self, x1, y1, x2, y2):
        self.rects.append((x1, self.height - y2, x2 - x1, y2 - y1))

    def get_results(self, box):
        ship(0, -self.depth, box)
        return (self.width,
                self.height + self.depth,
                self.depth,
                self.glyphs,
                self.rects,
                self.fonts_object.get_used_characters())

class MathtextBackendSvg(MathtextBackend):
    def __init__(self):
        self.svg_glyphs = []
        self.svg_rects = []

    def render_glyph(self, ox, oy, info):
        oy = self.height - oy + info.offset
        thetext = unichr(info.num)
        self.svg_glyphs.append(
            (info.font, info.fontsize, thetext, ox, oy, info.metrics))

    def render_rect_filled(self, x1, y1, x2, y2):
        self.svg_rects.append(
            (x1, self.height - y1 + 1, x2 - x1, y2 - y1))

    def get_results(self, box):
        ship(0, -self.depth, box)
        svg_elements = Bunch(svg_glyphs = self.svg_glyphs,
                             svg_rects = self.svg_rects)
        return (self.width,
                self.height + self.depth,
                self.depth,
                svg_elements,
                self.fonts_object.get_used_characters())

class MathtextBackendCairo(MathtextBackend):
    def __init__(self):
        self.glyphs = []
        self.rects = []

    def render_glyph(self, ox, oy, info):
        oy = oy - info.offset - self.height
        thetext = unichr(info.num)
        self.glyphs.append(
            (info.font, info.fontsize, thetext, ox, oy))

    def render_rect_filled(self, x1, y1, x2, y2):
        self.rects.append(
            (x1, y1 - self.height, x2 - x1, y2 - y1))

    def get_results(self, box):
        ship(0, -self.depth, box)
        return (self.width,
                self.height + self.depth,
                self.depth,
                self.glyphs,
                self.rects)

class Fonts(object):
    """
    An abstract base class for fonts that want to render mathtext

    The class must be able to take symbol keys and font file names and
    return the character metrics.  It also delegates to a backend class
    to do the actual drawing.
    """

    def __init__(self, default_font_prop, mathtext_backend):
        """default_font_prop: A FontProperties object to use for the
        default non-math font, or the base font for Unicode font
        rendering.
        mathtext_backend: A subclass of MathTextBackend used to
        delegate the actual rendering."""
        self.default_font_prop = default_font_prop
        self.mathtext_backend = mathtext_backend
        # Make these classes doubly-linked
        self.mathtext_backend.fonts_object = self
        self.used_characters = {}

    def destroy(self):
        """Fix any cyclical references before the object is about
        to be destroyed."""
        self.used_characters = None
        
    def get_kern(self, font1, sym1, fontsize1,
                 font2, sym2, fontsize2, dpi):
        """
        Get the kerning distance for font between sym1 and sym2.

        fontX: one of the TeX font names, tt, it, rm, cal, sf, bf or
               default (non-math)
        symX:  a symbol in raw TeX form. e.g. '1', 'x' or '\sigma'
        fontsizeX: the fontsize in points
        dpi: the current dots-per-inch

        sym is a single symbol(alphanum, punct) or a special symbol
        like \sigma.

        """
        return 0.

    def get_metrics(self, font, sym, fontsize, dpi):
        """
        font: one of the TeX font names, tt, it, rm, cal, sf, bf or
               default (non-math)
        sym:  a symbol in raw TeX form. e.g. '1', 'x' or '\sigma'
        fontsize: font size in points
        dpi: current dots-per-inch

          advance
          height
          width
          xmin, xmax, ymin, ymax  - the ink rectangle of the glyph
          iceberg - the distance from the baseline to the top of the glyph.
             horiBearingY in Truetype parlance, height in TeX parlance
        """
        info = self._get_info(font, sym, fontsize, dpi)
        return info.metrics

    def set_canvas_size(self, w, h, d):
        'Dimension the drawing canvas; may be a noop'
        self.width, self.height, self.depth = ceil(w), ceil(h), ceil(d)
        self.mathtext_backend.set_canvas_size(self.width, self.height, self.depth)

    def render_glyph(self, ox, oy, facename, sym, fontsize, dpi):
        info = self._get_info(facename, sym, fontsize, dpi)
        realpath, stat_key = get_realpath_and_stat(info.font.fname)
        used_characters = self.used_characters.setdefault(
            stat_key, (realpath, Set()))
        used_characters[1].update(unichr(info.num))
        self.mathtext_backend.render_glyph(ox, oy, info)

    def render_rect_filled(self, x1, y1, x2, y2):
        self.mathtext_backend.render_rect_filled(x1, y1, x2, y2)

    def get_xheight(self, font, fontsize, dpi):
        raise NotImplementedError()

    def get_underline_thickness(self, font, fontsize, dpi):
        raise NotImplementedError()

    def get_used_characters(self):
        return self.used_characters

    def get_results(self, box):
        return self.mathtext_backend.get_results(box)

    def get_sized_alternatives_for_symbol(self, fontname, sym):
        """
        Override if your font provides multiple sizes of the same
        symbol.
        """
        return [(fontname, sym)]

class TruetypeFonts(Fonts):
    """
    A generic base class for all font setups that use Truetype fonts
    (through ft2font)
    """
    basepath = os.path.join( get_data_path(), 'fonts' )

    class CachedFont:
        def __init__(self, font):
            self.font     = font
            self.charmap  = font.get_charmap()
            self.glyphmap = dict(
                [(glyphind, ccode) for ccode, glyphind in self.charmap.iteritems()])

        def __repr__(self):
            return repr(self.font)

    def __init__(self, default_font_prop, mathtext_backend):
        Fonts.__init__(self, default_font_prop, mathtext_backend)
        self.glyphd           = {}
        self.fonts            = {}

        filename = findfont(default_font_prop)
        default_font = self.CachedFont(FT2Font(str(filename)))

        self.fonts['default'] = default_font

    def destroy(self):
        self.glyphd = None
        for cached_font in self.fonts.values():
            cached_font.charmap = None
            cached_font.glyphmap = None
            cached_font.font = None
        Fonts.destroy(self)
        
    def _get_font(self, font):
        """Looks up a CachedFont with its charmap and inverse charmap.
        font may be a TeX font name (cal, rm, it etc.), or postscript name."""
        if font in self.fontmap:
            basename = self.fontmap[font]
        else:
            basename = font

        cached_font = self.fonts.get(basename)
        if cached_font is None:
            font = FT2Font(basename)
            cached_font = self.CachedFont(font)
            self.fonts[basename] = cached_font
            self.fonts[font.postscript_name] = cached_font
            self.fonts[font.postscript_name.lower()] = cached_font
        return cached_font

    def _get_offset(self, cached_font, glyph, fontsize, dpi):
        if cached_font.font.postscript_name == 'Cmex10':
            return glyph.height/64.0/2.0 + 256.0/64.0 * dpi/72.0
        return 0.

    def _get_info (self, fontname, sym, fontsize, dpi, mark_as_used=True):
        'load the cmfont, metrics and glyph with caching'
        key = fontname, sym, fontsize, dpi
        bunch = self.glyphd.get(key)
        if bunch is not None:
            return bunch

        cached_font, num, symbol_name, fontsize, slanted = \
            self._get_glyph(fontname, sym, fontsize)

        font = cached_font.font
        font.set_size(fontsize, dpi)
        glyph = font.load_char(
            num,
            flags=self.mathtext_backend.get_hinting_type())

        xmin, ymin, xmax, ymax = [val/64.0 for val in glyph.bbox]
        offset = self._get_offset(cached_font, glyph, fontsize, dpi)
        metrics = Bunch(
            advance = glyph.linearHoriAdvance/65536.0,
            height  = glyph.height/64.0,
            width   = glyph.width/64.0,
            xmin    = xmin,
            xmax    = xmax,
            ymin    = ymin+offset,
            ymax    = ymax+offset,
            # iceberg is the equivalent of TeX's "height"
            iceberg = glyph.horiBearingY/64.0 + offset,
            slanted = slanted
            )

        result = self.glyphd[key] = Bunch(
            font            = font,
            fontsize        = fontsize,
            postscript_name = font.postscript_name,
            metrics         = metrics,
            symbol_name     = symbol_name,
            num             = num,
            glyph           = glyph,
            offset          = offset
            )
        return result

    def get_xheight(self, font, fontsize, dpi):
        cached_font = self._get_font(font)
        cached_font.font.set_size(fontsize, dpi)
        pclt = cached_font.font.get_sfnt_table('pclt')
        if pclt is None:
            # Some fonts don't store the xHeight, so we do a poor man's xHeight
            metrics = self.get_metrics(font, 'x', fontsize, dpi)
            return metrics.iceberg
        xHeight = pclt['xHeight'] / 64.0
        return xHeight

    def get_underline_thickness(self, font, fontsize, dpi):
        cached_font = self._get_font(font)
        return max(1.0, cached_font.font.underline_thickness / 64.0 / fontsize * 10.0)

    def get_kern(self, font1, sym1, fontsize1,
                 font2, sym2, fontsize2, dpi):
        if font1 == font2 and fontsize1 == fontsize2:
            info1 = self._get_info(font1, sym1, fontsize1, dpi)
            info2 = self._get_info(font2, sym2, fontsize2, dpi)
            font = info1.font
            return font.get_kerning(info1.num, info2.num, KERNING_DEFAULT) / 64.0
        return 0.0

class BakomaFonts(TruetypeFonts):
    """
    Use the Bakoma true type fonts for rendering
    """
    _fontmap = { 'cal' : 'cmsy10',
                 'rm'  : 'cmr10',
                 'tt'  : 'cmtt10',
                 'it'  : 'cmmi10',
                 'bf'  : 'cmb10',
                 'sf'  : 'cmss10',
                 'ex'  : 'cmex10'
                 }
    fontmap = {}

    def __init__(self, *args, **kwargs):
        TruetypeFonts.__init__(self, *args, **kwargs)
        if not len(self.fontmap):
            for key, val in self._fontmap.iteritems():
                fullpath = os.path.join(self.basepath, 'ttf', val + ".ttf")
                self.fontmap[key] = fullpath
                self.fontmap[val] = fullpath

    _slanted_symbols = Set(r"\int \oint".split())

    def _get_glyph(self, fontname, sym, fontsize):
        symbol_name = None
        if fontname in self.fontmap and latex_to_bakoma.has_key(sym):
            basename, num = latex_to_bakoma[sym]
            slanted = (basename == "cmmi10") or sym in self._slanted_symbols
            cached_font = self._get_font(basename)
            symbol_name = cached_font.font.get_glyph_name(num)
            num = cached_font.glyphmap[num]
        elif len(sym) == 1:
            slanted = (fontname == "it")
            cached_font = self._get_font(fontname)
            num = ord(sym)
            gid = cached_font.charmap.get(num)
            if gid is not None:
                symbol_name = cached_font.font.get_glyph_name(
                    cached_font.charmap[num])

        if symbol_name is None:
            warn("Unrecognized symbol '%s'. Substituting with a dummy symbol."
                 % sym.encode('ascii', 'backslashreplace'), MathTextWarning)
            fontname = 'it'
            cached_font = self._get_font(fontname)
            num = 0x3F # currency character, for lack of anything better
            gid = cached_font.charmap[num]
            symbol_name = cached_font.font.get_glyph_name(gid)
            slanted = False

        return cached_font, num, symbol_name, fontsize, slanted

    # The Bakoma fonts contain many pre-sized alternatives for the
    # delimiters.  The AutoSizedChar class will use these alternatives
    # and select the best (closest sized) glyph.
    _size_alternatives = {
        '('          : [('rm', '('), ('ex', '\xa1'), ('ex', '\xb3'),
                        ('ex', '\xb5'), ('ex', '\xc3')],
        ')'          : [('rm', ')'), ('ex', '\xa2'), ('ex', '\xb4'),
                        ('ex', '\xb6'), ('ex', '\x21')],
        '{'          : [('cal', '{'), ('ex', '\xa9'), ('ex', '\x6e'),
                        ('ex', '\xbd'), ('ex', '\x28')],
        '}'          : [('cal', '}'), ('ex', '\xaa'), ('ex', '\x6f'),
                        ('ex', '\xbe'), ('ex', '\x29')],
        # The fourth size of '[' is mysteriously missing from the BaKoMa
        # font, so I've ommitted it for both '[' and ']'
        '['          : [('rm', '['), ('ex', '\xa3'), ('ex', '\x68'),
                        ('ex', '\x22')],
        ']'          : [('rm', ']'), ('ex', '\xa4'), ('ex', '\x69'),
                        ('ex', '\x23')],
        r'\lfloor'   : [('ex', '\xa5'), ('ex', '\x6a'),
                        ('ex', '\xb9'), ('ex', '\x24')],
        r'\rfloor'   : [('ex', '\xa6'), ('ex', '\x6b'),
                        ('ex', '\xba'), ('ex', '\x25')],
        r'\lceil'    : [('ex', '\xa7'), ('ex', '\x6c'),
                        ('ex', '\xbb'), ('ex', '\x26')],
        r'\rceil'    : [('ex', '\xa8'), ('ex', '\x6d'),
                        ('ex', '\xbc'), ('ex', '\x27')],
        r'\langle'   : [('ex', '\xad'), ('ex', '\x44'),
                        ('ex', '\xbf'), ('ex', '\x2a')],
        r'\rangle'   : [('ex', '\xae'), ('ex', '\x45'),
                        ('ex', '\xc0'), ('ex', '\x2b')],
        r'\__sqrt__' : [('ex', '\x70'), ('ex', '\x71'),
                        ('ex', '\x72'), ('ex', '\x73')],
        r'\backslash': [('ex', '\xb2'), ('ex', '\x2f'),
                        ('ex', '\xc2'), ('ex', '\x2d')],
        r'/'         : [('rm', '/'), ('ex', '\xb1'), ('ex', '\x2e'),
                        ('ex', '\xcb'), ('ex', '\x2c')],
        r'\widehat'  : [('rm', '\x5e'), ('ex', '\x62'), ('ex', '\x63'),
                        ('ex', '\x64')],
        r'\widetilde': [('rm', '\x7e'), ('ex', '\x65'), ('ex', '\x66'),
                        ('ex', '\x67')]
        }

    for alias, target in [('\leftparen', '('),
                          ('\rightparent', ')'),
                          ('\leftbrace', '{'),
                          ('\rightbrace', '}'),
                          ('\leftbracket', '['),
                          ('\rightbracket', ']')]:
        _size_alternatives[alias] = _size_alternatives[target]

    def get_sized_alternatives_for_symbol(self, fontname, sym):
        alternatives = self._size_alternatives.get(sym)
        if alternatives:
            return alternatives
        return [(fontname, sym)]

class UnicodeFonts(TruetypeFonts):
    """An abstract base class for handling Unicode fonts.
    """

    fontmap = {}
    use_cmex = True
    
    def __init__(self, *args, **kwargs):
        # This must come first so the backend's owner is set correctly
        if rcParams['mathtext.fallback_to_cm']:
            self.cm_fallback = BakomaFonts(*args, **kwargs)
        else:
            self.cm_fallback = None
        TruetypeFonts.__init__(self, *args, **kwargs)
        if not len(self.fontmap):
            for texfont in "cal rm tt it bf sf".split():
                prop = rcParams['mathtext.' + texfont]
                font = findfont(prop)
                self.fontmap[texfont] = font
            prop = FontProperties('cmex10')
            font = findfont(prop)
            self.fontmap['ex'] = font

    _slanted_symbols = Set(r"\int \oint".split())
            
    def _get_glyph(self, fontname, sym, fontsize):
        found_symbol = False

        if self.use_cmex:
            uniindex = latex_to_cmex.get(sym)
            if uniindex is not None:
                fontname = 'ex'
                found_symbol = True
                
        if not found_symbol:
            try:
                uniindex = get_unicode_index(sym)
                found_symbol = True
            except ValueError:
                uniindex = ord('?')
                warn("No TeX to unicode mapping for '%s'" %
                     sym.encode('ascii', 'backslashreplace'),
                     MathTextWarning)

        # Only characters in the "Letter" class should be italicized in 'it'
        # mode.  Greek capital letters should be Roman.
        if found_symbol:
            new_fontname = fontname

            if fontname == 'it':
                unistring = unichr(uniindex)
                if (not unicodedata.category(unistring).startswith("L")
                    or unicodedata.name(unistring).startswith("GREEK CAPITAL")):
                    new_fontname = 'rm'

            slanted = (new_fontname == 'it') or sym in self._slanted_symbols
            cached_font = self._get_font(new_fontname)
            try:
                glyphindex = cached_font.charmap[uniindex]
            except KeyError:
                warn("Font '%s' does not have a glyph for '%s'" %
                     (cached_font.font.postscript_name,
                      sym.encode('ascii', 'backslashreplace')),
                     MathTextWarning)
                found_symbol = False

        if not found_symbol:
            if self.cm_fallback:
                warn("Substituting with a symbol from Computer Modern.",
                     MathTextWarning)
                return self.cm_fallback._get_glyph(fontname, sym, fontsize)
            else:
                warn("Substituting with a dummy symbol.", MathTextWarning)
                fontname = 'rm'
                new_fontname = fontname
                cached_font = self._get_font(fontname)
                uniindex = 0xA4 # currency character, for lack of anything better
                glyphindex = cached_font.charmap[uniindex]
                slanted = False

        symbol_name = cached_font.font.get_glyph_name(glyphindex)
        return cached_font, uniindex, symbol_name, fontsize, slanted

    def get_sized_alternatives_for_symbol(self, fontname, sym):
        if self.cm_fallback:
            return self.cm_fallback.get_sized_alternatives_for_symbol(
                fontname, sym)
        return [(fontname, sym)]

class StixFonts(UnicodeFonts):
    _fontmap = { 'rm'  : 'STIXGeneral',
                 'tt'  : 'VeraMono',
                 'it'  : 'STIXGeneralItalic',
                 'bf'  : 'STIXGeneralBol',
                 'sf'  : 'Vera',
                 'nonunirm' : 'STIXNonUni',
                 'nonuniit' : 'STIXNonUniIta',
                 'nonunibf' : 'STIXNonUniBol',
                 
                 0 : 'STIXGeneral',
                 1 : 'STIXSiz1Sym',
                 2 : 'STIXSiz2Sym',
                 3 : 'STIXSiz3Sym',
                 4 : 'STIXSiz4Sym',
                 5 : 'STIXSiz5Sym'
                 }
    fontmap = {}
    use_cmex = False
    cm_fallback = False

    def __init__(self, *args, **kwargs):
        TruetypeFonts.__init__(self, *args, **kwargs)
        if not len(self.fontmap):
            for key, name in self._fontmap.iteritems():
                fullpath = os.path.join(self.basepath, 'ttf', name + ".ttf")
                self.fontmap[key] = fullpath
                self.fontmap[name] = fullpath

    def _get_glyph(self, fontname, sym, fontsize):
        # Handle calligraphic letters
        if fontname == 'cal':
            if len(sym) != 1 or ord(sym) < ord('A') or ord(sym) > ord('Z'):
                raise ValueError(r"Sym '%s' is not available in \mathcal font" % sym)
            fontname = 'nonuniit'
            sym = unichr(ord(sym) + 0xe22d - ord('A'))

        # Handle private use area glyphs
        if (fontname in ('it', 'rm', 'bf') and
            len(sym) == 1 and ord(sym) >= 0xe000 and ord(sym) <= 0xf8ff):
            fontname = 'nonuni' + fontname

        return UnicodeFonts._get_glyph(self, fontname, sym, fontsize)
                
    _size_alternatives = {}
    def get_sized_alternatives_for_symbol(self, fontname, sym):
        alternatives = self._size_alternatives.get(sym)
        if alternatives:
            return alternatives

        alternatives = []
        try:
            uniindex = get_unicode_index(sym)
        except ValueError:
            return [(fontname, sym)]

        for i in range(6):
            cached_font = self._get_font(i)
            glyphindex = cached_font.charmap.get(uniindex)
            if glyphindex is not None:
                alternatives.append((i, unichr(uniindex)))

        self._size_alternatives[sym] = alternatives
        return alternatives
    
class StandardPsFonts(Fonts):
    """
    Use the standard postscript fonts for rendering to backend_ps

    Unlike the other font classes, BakomaFont and UnicodeFont, this
    one requires the Ps backend.
    """
    basepath = os.path.join( get_data_path(), 'fonts', 'afm' )

    fontmap = { 'cal' : 'pzcmi8a',  # Zapf Chancery
                'rm'  : 'pncr8a',   # New Century Schoolbook
                'tt'  : 'pcrr8a',   # Courier
                'it'  : 'pncri8a',  # New Century Schoolbook Italic
                'sf'  : 'phvr8a',   # Helvetica
                'bf'  : 'pncb8a',   # New Century Schoolbook Bold
                None  : 'psyr'      # Symbol
                }

    def __init__(self, default_font_prop):
        Fonts.__init__(self, default_font_prop, MathtextBackendPs())
        self.glyphd = {}
        self.fonts = {}

        filename = findfont(default_font_prop, fontext='afm')
        default_font = AFM(file(filename, 'r'))
        default_font.fname = filename

        self.fonts['default'] = default_font
        self.pswriter = StringIO()

    def _get_font(self, font):
        if font in self.fontmap:
            basename = self.fontmap[font]
        else:
            basename = font

        cached_font = self.fonts.get(basename)
        if cached_font is None:
            fname = os.path.join(self.basepath, basename + ".afm")
            cached_font = AFM(file(fname, 'r'))
            cached_font.fname = fname
            self.fonts[basename] = cached_font
            self.fonts[cached_font.get_fontname()] = cached_font
        return cached_font

    def _get_info (self, fontname, sym, fontsize, dpi):
        'load the cmfont, metrics and glyph with caching'
        key = fontname, sym, fontsize, dpi
        tup = self.glyphd.get(key)

        if tup is not None:
            return tup

        # Only characters in the "Letter" class should really be italicized.
        # This class includes greek letters, so we're ok
        if (fontname == 'it' and
            (len(sym) > 1 or
             not unicodedata.category(unicode(sym)).startswith("L"))):
            fontname = 'rm'

        found_symbol = False

        if latex_to_standard.has_key(sym):
            fontname, num = latex_to_standard[sym]
            glyph = chr(num)
            found_symbol = True
        elif len(sym) == 1:
            glyph = sym
            num = ord(glyph)
            found_symbol = True
        else:
            warn("No TeX to built-in Postscript mapping for '%s'" % sym,
                 MathTextWarning)

        slanted = (fontname == 'it')
        font = self._get_font(fontname)

        if found_symbol:
            try:
                symbol_name = font.get_name_char(glyph)
            except KeyError:
                warn("No glyph in standard Postscript font '%s' for '%s'" %
                     (font.postscript_name, sym),
                     MathTextWarning)
                found_symbol = False

        if not found_symbol:
            glyph = sym = '?'
            num = ord(glyph)
            symbol_name = font.get_name_char(glyph)

        offset = 0

        scale = 0.001 * fontsize

        xmin, ymin, xmax, ymax = [val * scale
                                  for val in font.get_bbox_char(glyph)]
        metrics = Bunch(
            advance  = font.get_width_char(glyph) * scale,
            width    = font.get_width_char(glyph) * scale,
            height   = font.get_height_char(glyph) * scale,
            xmin = xmin,
            xmax = xmax,
            ymin = ymin+offset,
            ymax = ymax+offset,
            # iceberg is the equivalent of TeX's "height"
            iceberg = ymax + offset,
            slanted = slanted
            )

        self.glyphd[key] = Bunch(
            font            = font,
            fontsize        = fontsize,
            postscript_name = font.get_fontname(),
            metrics         = metrics,
            symbol_name     = symbol_name,
            num             = num,
            glyph           = glyph,
            offset          = offset
            )

        return self.glyphd[key]

    def get_kern(self, font1, sym1, fontsize1,
                 font2, sym2, fontsize2, dpi):
        if font1 == font2 and fontsize1 == fontsize2:
            info1 = self._get_info(font1, sym1, fontsize1, dpi)
            info2 = self._get_info(font2, sym2, fontsize2, dpi)
            font = info1.font
            return (font.get_kern_dist(info1.glyph, info2.glyph)
                    * 0.001 * fontsize1)
        return 0.0

    def get_xheight(self, font, fontsize, dpi):
        cached_font = self._get_font(font)
        return cached_font.get_xheight() * 0.001 * fontsize

    def get_underline_thickness(self, font, fontsize, dpi):
        cached_font = self._get_font(font)
        return cached_font.get_underline_thickness() * 0.001 * fontsize

##############################################################################
# TeX-LIKE BOX MODEL

# The following is based directly on the document 'woven' from the
# TeX82 source code.  This information is also available in printed
# form:
#
#    Knuth, Donald E.. 1986.  Computers and Typesetting, Volume B:
#    TeX: The Program.  Addison-Wesley Professional.
#
# The most relevant "chapters" are:
#    Data structures for boxes and their friends
#    Shipping pages out (Ship class)
#    Packaging (hpack and vpack)
#    Data structures for math mode
#    Subroutines for math mode
#    Typesetting math formulas
#
# Many of the docstrings below refer to a numbered "node" in that
# book, e.g. @123
#
# Note that (as TeX) y increases downward, unlike many other parts of
# matplotlib.

# How much text shrinks when going to the next-smallest level
SHRINK_FACTOR   = 0.7
GROW_FACTOR     = 1.0 / SHRINK_FACTOR
# The number of different sizes of chars to use, beyond which they will not
# get any smaller
NUM_SIZE_LEVELS = 4
# Percentage of x-height of additional horiz. space after sub/superscripts
SCRIPT_SPACE    = 0.2
# Percentage of x-height that sub/superscripts drop below the baseline
SUBDROP         = 0.3
# Percentage of x-height that superscripts drop below the baseline
SUP1            = 0.7
# Percentage of x-height that subscripts drop below the baseline
SUB1            = 0.0
# Percentage of x-height that superscripts are offset relative to the subscript
DELTA           = 0.18

class MathTextWarning(Warning):
    pass

class Node(object):
    """A node in the TeX box model
    @133
    """
    def __init__(self):
        self.size = 0

    def __repr__(self):
        return self.__internal_repr__()

    def __internal_repr__(self):
        return self.__class__.__name__

    def get_kerning(self, next):
        return 0.0

    def shrink(self):
        """Shrinks one level smaller.  There are only three levels of sizes,
        after which things will no longer get smaller."""
        self.size += 1

    def grow(self):
        """Grows one level larger.  There is no limit to how big something
        can get."""
        self.size -= 1

    def render(self, x, y):
        pass

class Box(Node):
    """Represents any node with a physical location.
    @135"""
    def __init__(self, width, height, depth):
        Node.__init__(self)
        self.width  = width
        self.height = height
        self.depth  = depth

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.width  *= SHRINK_FACTOR
            self.height *= SHRINK_FACTOR
            self.depth  *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        self.width  *= GROW_FACTOR
        self.height *= GROW_FACTOR
        self.depth  *= GROW_FACTOR

    def render(self, x1, y1, x2, y2):
        pass

class Vbox(Box):
    def __init__(self, height, depth):
        Box.__init__(self, 0., height, depth)

class Hbox(Box):
    def __init__(self, width):
        Box.__init__(self, width, 0., 0.)

class Char(Node):
    """Represents a single character.  Unlike TeX, the font
    information and metrics are stored with each Char to make it
    easier to lookup the font metrics when needed.  Note that TeX
    boxes have a width, height, and depth, unlike Type1 and Truetype
    which use a full bounding box and an advance in the x-direction.
    The metrics must be converted to the TeX way, and the advance (if
    different from width) must be converted into a Kern node when the
    Char is added to its parent Hlist.
    @134"""
    def __init__(self, c, state):
        Node.__init__(self)
        self.c = c
        self.font_output = state.font_output
        assert isinstance(state.font, (str, unicode, int))
        self.font = state.font
        self.fontsize = state.fontsize
        self.dpi = state.dpi
        # The real width, height and depth will be set during the
        # pack phase, after we know the real fontsize
        self._update_metrics()

    def __internal_repr__(self):
        return '`%s`' % self.c

    def _update_metrics(self):
        metrics = self._metrics = self.font_output.get_metrics(
            self.font, self.c, self.fontsize, self.dpi)
        if self.c == ' ':
            self.width = metrics.advance
        else:
            self.width = metrics.width
        self.height = metrics.iceberg
        self.depth = -(metrics.iceberg - metrics.height)

    def is_slanted(self):
        return self._metrics.slanted

    def get_kerning(self, next):
        """Return the amount of kerning between this and the given
        character.  Called when characters are strung together into
        Hlists to create Kern nodes."""
        advance = self._metrics.advance - self.width
        kern = 0.
        if isinstance(next, Char):
            kern = self.font_output.get_kern(
                self.font, self.c, self.fontsize,
                next.font, next.c, next.fontsize,
                self.dpi)
        return advance + kern

    def render(self, x, y):
        """Render the character to the canvas"""
        self.font_output.render_glyph(
            x, y,
            self.font, self.c, self.fontsize, self.dpi)

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.fontsize *= SHRINK_FACTOR
            self.width    *= SHRINK_FACTOR
            self.height   *= SHRINK_FACTOR
            self.depth    *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        self.fontsize *= GROW_FACTOR
        self.width    *= GROW_FACTOR
        self.height   *= GROW_FACTOR
        self.depth    *= GROW_FACTOR

class Accent(Char):
    """The font metrics need to be dealt with differently for accents, since they
    are already offset correctly from the baseline in TrueType fonts."""
    def _update_metrics(self):
        metrics = self._metrics = self.font_output.get_metrics(
            self.font, self.c, self.fontsize, self.dpi)
        self.width = metrics.xmax - metrics.xmin
        self.height = metrics.ymax - metrics.ymin
        self.depth = 0

    def shrink(self):
        Char.shrink(self)
        self._update_metrics()

    def grow(self):
        Char.grow(self)
        self._update_metrics()

    def render(self, x, y):
        """Render the character to the canvas"""
        self.font_output.render_glyph(
            x - self._metrics.xmin, y + self._metrics.ymin,
            self.font, self.c, self.fontsize, self.dpi)

class List(Box):
    """A list of nodes (either horizontal or vertical).
    @135"""
    def __init__(self, elements):
        Box.__init__(self, 0., 0., 0.)
        self.shift_amount = 0.   # An arbitrary offset
        self.children     = elements # The child nodes of this list
        # The following parameters are set in the vpack and hpack functions
        self.glue_set     = 0.   # The glue setting of this list
        self.glue_sign    = 0    # 0: normal, -1: shrinking, 1: stretching
        self.glue_order   = 0    # The order of infinity (0 - 3) for the glue

    def __repr__(self):
        return '[%s <%.02f %.02f %.02f %.02f> %s]' % (
            self.__internal_repr__(),
            self.width, self.height,
            self.depth, self.shift_amount,
            ' '.join([repr(x) for x in self.children]))

    def _determine_order(self, totals):
        """A helper function to determine the highest order of glue
        used by the members of this list.  Used by vpack and hpack."""
        o = 0
        for i in range(len(totals) - 1, 0, -1):
            if totals[i] != 0.0:
                o = i
                break
        return o

    def _set_glue(self, x, sign, totals, error_type):
        o = self._determine_order(totals)
        self.glue_order = o
        self.glue_sign = sign
        if totals[o] != 0.:
            self.glue_set = x / totals[o]
        else:
            self.glue_sign = 0
            self.glue_ratio = 0.
        if o == 0:
            if len(self.children):
                warn("%s %s: %r" % (error_type, self.__class__.__name__, self),
                     MathTextWarning)

    def shrink(self):
        for child in self.children:
            child.shrink()
        Box.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.shift_amount *= SHRINK_FACTOR
            self.glue_set     *= SHRINK_FACTOR

    def grow(self):
        for child in self.children:
            child.grow()
        Box.grow(self)
        self.shift_amount *= GROW_FACTOR
        self.glue_set     *= GROW_FACTOR

class Hlist(List):
    """A horizontal list of boxes.
    @135"""
    def __init__(self, elements, w=0., m='additional', do_kern=True):
        List.__init__(self, elements)
        if do_kern:
            self.kern()
        self.hpack()

    def kern(self):
        """Insert Kern nodes between Chars to set kerning.  The
        Chars themselves determine the amount of kerning they need
        (in get_kerning), and this function just creates the linked
        list in the correct way."""
        new_children = []
        num_children = len(self.children)
        if num_children:
            for i in range(num_children):
                elem = self.children[i]
                if i < num_children - 1:
                    next = self.children[i + 1]
                else:
                    next = None

                new_children.append(elem)
                kerning_distance = elem.get_kerning(next)
                if kerning_distance != 0.:
                    kern = Kern(kerning_distance)
                    new_children.append(kern)
            self.children = new_children

    def hpack(self, w=0., m='additional'):
        """The main duty of hpack is to compute the dimensions of the
        resulting boxes, and to adjust the glue if one of those dimensions is
        pre-specified. The computed sizes normally enclose all of the material
        inside the new box; but some items may stick out if negative glue is
        used, if the box is overfull, or if a \vbox includes other boxes that
        have been shifted left.

        w: specifies a width
        m: is either 'exactly' or 'additional'.

        Thus, hpack(w, exactly) produces a box whose width is exactly w, while
        hpack (w, additional ) yields a box whose width is the natural width
        plus w.  The default values produce a box with the natural width.
        @644, @649"""
        # I don't know why these get reset in TeX.  Shift_amount is pretty
        # much useless if we do.
        #self.shift_amount = 0.
        h = 0.
        d = 0.
        x = 0.
        total_stretch = [0.] * 4
        total_shrink = [0.] * 4
        for p in self.children:
            if isinstance(p, Char):
                x += p.width
                h = max(h, p.height)
                d = max(d, p.depth)
            elif isinstance(p, Box):
                x += p.width
                if not isinf(p.height) and not isinf(p.depth):
                    s = getattr(p, 'shift_amount', 0.)
                    h = max(h, p.height - s)
                    d = max(d, p.depth + s)
            elif isinstance(p, Glue):
                glue_spec = p.glue_spec
                x += glue_spec.width
                total_stretch[glue_spec.stretch_order] += glue_spec.stretch
                total_shrink[glue_spec.shrink_order] += glue_spec.shrink
            elif isinstance(p, Kern):
                x += p.width
        self.height = h
        self.depth = d

        if m == 'additional':
            w += x
        self.width = w
        x = w - x

        if x == 0.:
            self.glue_sign = 0
            self.glue_order = 0
            self.glue_ratio = 0.
            return
        if x > 0.:
            self._set_glue(x, 1, total_stretch, "Overfull")
        else:
            self._set_glue(x, -1, total_shrink, "Underfull")

class Vlist(List):
    """A vertical list of boxes.
    @137"""
    def __init__(self, elements, h=0., m='additional'):
        List.__init__(self, elements)
        self.vpack()

    def vpack(self, h=0., m='additional', l=float(inf)):
        """The main duty of vpack is to compute the dimensions of the
        resulting boxes, and to adjust the glue if one of those dimensions is
        pre-specified.

        h: specifies a height
        m: is either 'exactly' or 'additional'.
        l: a maximum height

        Thus, vpack(h, exactly) produces a box whose width is exactly w, while
        vpack(w, additional) yields a box whose width is the natural width
        plus w.  The default values produce a box with the natural width.
        @644, @668"""
        # I don't know why these get reset in TeX.  Shift_amount is pretty
        # much useless if we do.
        # self.shift_amount = 0.
        w = 0.
        d = 0.
        x = 0.
        total_stretch = [0.] * 4
        total_shrink = [0.] * 4
        for p in self.children:
            if isinstance(p, Box):
                x += d + p.height
                d = p.depth
                if not isinf(p.width):
                    s = getattr(p, 'shift_amount', 0.)
                    w = max(w, p.width + s)
            elif isinstance(p, Glue):
                x += d
                d = 0.
                glue_spec = p.glue_spec
                x += glue_spec.width
                total_stretch[glue_spec.stretch_order] += glue_spec.stretch
                total_shrink[glue_spec.shrink_order] += glue_spec.shrink
            elif isinstance(p, Kern):
                x += d + p.width
                d = 0.
            elif isinstance(p, Char):
                raise RuntimeError("Internal mathtext error: Char node found in Vlist.")

        self.width = w
        if d > l:
            x += d - l
            self.depth = l
        else:
            self.depth = d

        if m == 'additional':
            h += x
        self.height = h
        x = h - x

        if x == 0:
            self.glue_sign = 0
            self.glue_order = 0
            self.glue_ratio = 0.
            return

        if x > 0.:
            self._set_glue(x, 1, total_stretch, "Overfull")
        else:
            self._set_glue(x, -1, total_shrink, "Underfull")

class Rule(Box):
    """A Rule node stands for a solid black rectangle; it has width,
    depth, and height fields just as in an Hlist. However, if any of these
    dimensions is inf, the actual value will be determined by running the
    rule up to the boundary of the innermost enclosing box. This is called
    a "running dimension." The width is never running in an Hlist; the
    height and depth are never running in a Vlist.
    @138"""
    def __init__(self, width, height, depth, state):
        Box.__init__(self, width, height, depth)
        self.font_output = state.font_output

    def render(self, x, y, w, h):
        self.font_output.render_rect_filled(x, y, x + w, y + h)

class Hrule(Rule):
    """Convenience class to create a horizontal rule."""
    def __init__(self, state):
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        height = depth = thickness * 0.5
        Rule.__init__(self, inf, height, depth, state)

class Vrule(Rule):
    """Convenience class to create a vertical rule."""
    def __init__(self, state):
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        Rule.__init__(self, thickness, inf, inf, state)

class Glue(Node):
    """Most of the information in this object is stored in the underlying
    GlueSpec class, which is shared between multiple glue objects.  (This
    is a memory optimization which probably doesn't matter anymore, but it's
    easier to stick to what TeX does.)
    @149, @152"""
    def __init__(self, glue_type, copy=False):
        Node.__init__(self)
        self.glue_subtype   = 'normal'
        if is_string_like(glue_type):
            glue_spec = GlueSpec.factory(glue_type)
        elif isinstance(glue_type, GlueSpec):
            glue_spec = glue_type
        else:
            raise ArgumentError("glue_type must be a glue spec name or instance.")
        if copy:
            glue_spec = glue_spec.copy()
        self.glue_spec      = glue_spec

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            if self.glue_spec.width != 0.:
                self.glue_spec = self.glue_spec.copy()
                self.glue_spec.width *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        if self.glue_spec.width != 0.:
            self.glue_spec = self.glue_spec.copy()
            self.glue_spec.width *= GROW_FACTOR

class GlueSpec(object):
    """@150, @151"""
    def __init__(self, width=0., stretch=0., stretch_order=0, shrink=0., shrink_order=0):
        self.width         = width
        self.stretch       = stretch
        self.stretch_order = stretch_order
        self.shrink        = shrink
        self.shrink_order  = shrink_order

    def copy(self):
        return GlueSpec(
            self.width,
            self.stretch,
            self.stretch_order,
            self.shrink,
            self.shrink_order)

    def factory(cls, glue_type):
        return cls._types[glue_type]
    factory = classmethod(factory)

GlueSpec._types = {
    'fil':         GlueSpec(0., 1., 1, 0., 0),
    'fill':        GlueSpec(0., 1., 2, 0., 0),
    'filll':       GlueSpec(0., 1., 3, 0., 0),
    'neg_fil':     GlueSpec(0., 0., 0, 1., 1),
    'neg_fill':    GlueSpec(0., 0., 0, 1., 2),
    'neg_filll':   GlueSpec(0., 0., 0, 1., 3),
    'empty':       GlueSpec(0., 0., 0, 0., 0),
    'ss':          GlueSpec(0., 1., 1, -1., 1)
}

# Some convenient ways to get common kinds of glue

class Fil(Glue):
    def __init__(self):
        Glue.__init__(self, 'fil')

class Fill(Glue):
    def __init__(self):
        Glue.__init__(self, 'fill')

class Filll(Glue):
    def __init__(self):
        Glue.__init__(self, 'filll')

class NegFil(Glue):
    def __init__(self):
        Glue.__init__(self, 'neg_fil')

class NegFill(Glue):
    def __init__(self):
        Glue.__init__(self, 'neg_fill')

class NegFilll(Glue):
    def __init__(self):
        Glue.__init__(self, 'neg_filll')

class SsGlue(Glue):
    def __init__(self):
        Glue.__init__(self, 'ss')

class HCentered(Hlist):
    """A convenience class to create an Hlist whose contents are centered
    within its enclosing box."""
    def __init__(self, elements):
        Hlist.__init__(self, [SsGlue()] + elements + [SsGlue()],
                       do_kern=False)

class VCentered(Hlist):
    """A convenience class to create an Vlist whose contents are centered
    within its enclosing box."""
    def __init__(self, elements):
        Vlist.__init__(self, [SsGlue()] + elements + [SsGlue()])

class Kern(Node):
    """A Kern node has a width field to specify a (normally negative)
    amount of spacing. This spacing correction appears in horizontal lists
    between letters like A and V when the font designer said that it looks
    better to move them closer together or further apart. A kern node can
    also appear in a vertical list, when its 'width' denotes additional
    spacing in the vertical direction.
    @155"""
    def __init__(self, width):
        Node.__init__(self)
        self.width = width

    def __repr__(self):
        return "k%.02f" % self.width

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.width *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        self.width *= GROW_FACTOR

class SubSuperCluster(Hlist):
    """This class is a sort of hack to get around that fact that this
    code doesn't parse to an mlist and then an hlist, but goes directly
    to hlists.  This lets us store enough information in the hlist itself,
    namely the nucleas, sub- and super-script, such that if another script
    follows that needs to be attached, it can be reconfigured on the fly."""
    def __init__(self):
        self.nucleus = None
        self.sub = None
        self.super = None
        Hlist.__init__(self, [])

class AutoHeightChar(Hlist):
    """A class that will create a character as close to the given height
    and depth as possible.  When using a font with multiple height versions
    of some characters (such as the BaKoMa fonts), the correct glyph will
    be selected, otherwise this will always just return a scaled version
    of the glyph."""
    def __init__(self, c, height, depth, state, always=False):
        alternatives = state.font_output.get_sized_alternatives_for_symbol(
            state.font, c)

        state = state.copy()
        target_total = height + depth
        for fontname, sym in alternatives:
            state.font = fontname
            char = Char(sym, state)
            if char.height + char.depth >= target_total:
                break

        factor = target_total / (char.height + char.depth)
        state.fontsize *= factor
        char = Char(sym, state)

        shift = (depth - char.depth)
        Hlist.__init__(self, [char])
        self.shift_amount = shift

class AutoWidthChar(Hlist):
    """A class that will create a character as close to the given width
    as possible.  When using a font with multiple width versions
    of some characters (such as the BaKoMa fonts), the correct glyph will
    be selected, otherwise this will always just return a scaled version
    of the glyph."""
    def __init__(self, c, width, state, always=False, char_class=Char):
        alternatives = state.font_output.get_sized_alternatives_for_symbol(
            state.font, c)

        state = state.copy()
        for fontname, sym in alternatives:
            state.font = fontname
            char = char_class(sym, state)
            if char.width >= width:
                break

        factor = width / char.width
        state.fontsize *= factor
        char = char_class(sym, state)

        Hlist.__init__(self, [char])

class Ship(object):
    """Once the boxes have been set up, this sends them to output.
    Since boxes can be inside of boxes inside of boxes, the main
    work of Ship is done by two mutually recursive routines, hlist_out
    and vlist_out , which traverse the Hlists and Vlists inside of
    horizontal and vertical boxes.  The global variables used in TeX to
    store state as it processes have become member variables here.
    @592."""
    def __call__(self, ox, oy, box):
        self.max_push    = 0 # Deepest nesting of push commands so far
        self.cur_s       = 0
        self.cur_v       = 0.
        self.cur_h       = 0.
        self.off_h       = ox
        self.off_v       = oy + box.height
        self.hlist_out(box)

    def clamp(value):
        if value < -1000000000.:
            return -1000000000.
        if value > 1000000000.:
            return 1000000000.
        return value
    clamp = staticmethod(clamp)

    def hlist_out(self, box):
        cur_g         = 0
        cur_glue      = 0.
        glue_order    = box.glue_order
        glue_sign     = box.glue_sign
        base_line     = self.cur_v
        left_edge     = self.cur_h
        self.cur_s    += 1
        self.max_push = max(self.cur_s, self.max_push)

        for p in box.children:
            if isinstance(p, Char):
                p.render(self.cur_h + self.off_h, self.cur_v + self.off_v)
                self.cur_h += p.width
            elif isinstance(p, List):
                # @623
                if len(p.children) == 0:
                    self.cur_h += p.width
                else:
                    edge = self.cur_h
                    self.cur_v = base_line + p.shift_amount
                    if isinstance(p, Hlist):
                        self.hlist_out(p)
                    else:
                        # p.vpack(box.height + box.depth, 'exactly')
                        self.vlist_out(p)
                    self.cur_h = edge + p.width
                    self.cur_v = base_line
            elif isinstance(p, Box):
                # @624
                rule_height = p.height
                rule_depth  = p.depth
                rule_width  = p.width
                if isinf(rule_height):
                    rule_height = box.height
                if isinf(rule_depth):
                    rule_depth = box.depth
                if rule_height > 0 and rule_width > 0:
                    self.cur_v = baseline + rule_depth
                    p.render(self.cur_h + self.off_h,
                             self.cur_v + self.off_v,
                             rule_width, rule_height)
                    self.cur_v = baseline
                self.cur_h += rule_width
            elif isinstance(p, Glue):
                # @625
                glue_spec = p.glue_spec
                rule_width = glue_spec.width - cur_g
                if glue_sign != 0: # normal
                    if glue_sign == 1: # stretching
                        if glue_spec.stretch_order == glue_order:
                            cur_glue += glue_spec.stretch
                            cur_g = round(self.clamp(float(box.glue_set) * cur_glue))
                    elif glue_spec.shrink_order == glue_order:
                        cur_glue += glue_spec.shrink
                        cur_g = round(self.clamp(float(box.glue_set) * cur_glue))
                rule_width += cur_g
                self.cur_h += rule_width
            elif isinstance(p, Kern):
                self.cur_h += p.width
        self.cur_s -= 1

    def vlist_out(self, box):
        cur_g         = 0
        cur_glue      = 0.
        glue_order    = box.glue_order
        glue_sign     = box.glue_sign
        self.cur_s    += 1
        self.max_push = max(self.max_push, self.cur_s)
        left_edge     = self.cur_h
        self.cur_v    -= box.height
        top_edge      = self.cur_v

        for p in box.children:
            if isinstance(p, List):
                if len(p.children) == 0:
                    self.cur_v += p.height + p.depth
                else:
                    self.cur_v += p.height
                    self.cur_h = left_edge + p.shift_amount
                    save_v = self.cur_v
                    p.width = box.width
                    if isinstance(p, Hlist):
                        self.hlist_out(p)
                    else:
                        self.vlist_out(p)
                    self.cur_v = save_v + p.depth
                    self.cur_h = left_edge
            elif isinstance(p, Box):
                rule_height = p.height
                rule_depth = p.depth
                rule_width = p.width
                if isinf(rule_width):
                    rule_width = box.width
                rule_height += rule_depth
                if rule_height > 0 and rule_depth > 0:
                    self.cur_v += rule_height
                    p.render(self.cur_h + self.off_h,
                             self.cur_v + self.off_v,
                             rule_width, rule_height)
            elif isinstance(p, Glue):
                glue_spec = p.glue_spec
                rule_height = glue_spec.width - cur_g
                if glue_sign != 0: # normal
                    if glue_sign == 1: # stretching
                        if glue_spec.stretch_order == glue_order:
                            cur_glue += glue_spec.stretch
                            cur_g = round(self.clamp(float(box.glue_set) * cur_glue))
                    elif glue_spec.shrink_order == glue_order: # shrinking
                        cur_glue += glue_spec.shrink
                        cur_g = round(self.clamp(float(box.glue_set) * cur_glue))
                rule_height += cur_g
                self.cur_v += rule_height
            elif isinstance(p, Kern):
                self.cur_v += p.width
            elif isinstance(p, Char):
                raise RuntimeError("Internal mathtext error: Char node found in vlist")
        self.cur_s -= 1

ship = Ship()

##############################################################################
# PARSER

def Error(msg):
    def raise_error(s, loc, toks):
        raise ParseFatalException(msg + "\n" + s)

    empty = Empty()
    empty.setParseAction(raise_error)
    return empty
    
class Parser(object):
    _binary_operators = Set(r'''
      + *
      \pm             \sqcap                   \rhd
      \mp             \sqcup                   \unlhd
      \times          \vee                     \unrhd
      \div            \wedge                   \oplus
      \ast            \setminus                \ominus
      \star           \wr                      \otimes
      \circ           \diamond                 \oslash
      \bullet         \bigtriangleup           \odot
      \cdot           \bigtriangledown         \bigcirc
      \cap            \triangleleft            \dagger
      \cup            \triangleright           \ddagger
      \uplus          \lhd                     \amalg'''.split())

    _relation_symbols = Set(r'''
      = < > :
      \leq            \geq             \equiv           \models
      \prec           \succ            \sim             \perp
      \preceq         \succeq          \simeq           \mid
      \ll             \gg              \asymp           \parallel
      \subset         \supset          \approx          \bowtie
      \subseteq       \supseteq        \cong            \Join
      \sqsubset       \sqsupset        \neq             \smile
      \sqsubseteq     \sqsupseteq      \doteq           \frown
      \in             \ni              \propto
      \vdash          \dashv'''.split())

    _arrow_symbols = Set(r'''
      \leftarrow              \longleftarrow           \uparrow
      \Leftarrow              \Longleftarrow           \Uparrow
      \rightarrow             \longrightarrow          \downarrow
      \Rightarrow             \Longrightarrow          \Downarrow
      \leftrightarrow         \longleftrightarrow      \updownarrow
      \Leftrightarrow         \Longleftrightarrow      \Updownarrow
      \mapsto                 \longmapsto              \nearrow
      \hookleftarrow          \hookrightarrow          \searrow
      \leftharpoonup          \rightharpoonup          \swarrow
      \leftharpoondown        \rightharpoondown        \nwarrow
      \rightleftharpoons      \leadsto'''.split())

    _spaced_symbols = _binary_operators | _relation_symbols | _arrow_symbols

    _punctuation_symbols = Set(r', ; . ! \ldotp \cdotp'.split())

    _overunder_symbols = Set(r'''
       \sum \prod \coprod \bigcap \bigcup \bigsqcup \bigvee
       \bigwedge \bigodot \bigotimes \bigoplus \biguplus
       '''.split())

    _overunder_functions = Set(
        r"lim liminf limsup sup max min".split())

    _dropsub_symbols = Set(r'''\int \oint'''.split())

    def __init__(self):
        # All forward declarations are here
        font = Forward().setParseAction(self.font).setName("font")
        latexfont = Forward()
        subsuper = Forward().setParseAction(self.subsuperscript).setName("subsuper")
        placeable = Forward().setName("placeable")
        simple = Forward().setName("simple")
        autoDelim = Forward().setParseAction(self.auto_sized_delimiter)
        self._expression = Forward().setParseAction(self.finish).setName("finish")

        float        = Regex(r"-?[0-9]+\.?[0-9]*")
        
        lbrace       = Literal('{').suppress()
        rbrace       = Literal('}').suppress()
        start_group  = (Optional(latexfont) + lbrace)
        start_group.setParseAction(self.start_group)
        end_group    = rbrace.copy()
        end_group.setParseAction(self.end_group)

        bslash       = Literal('\\')

        accent       = oneOf(self._accent_map.keys() + list(self._wide_accents))

        function     = oneOf("arccos csc ker min arcsin deg lg Pr arctan det "
                             "lim sec arg dim liminf sin cos exp limsup sinh "
                             "cosh gcd ln sup cot hom log tan coth inf max "
                             "tanh")

        fontname     = oneOf("rm cal it tt sf bf")
        latex2efont  = oneOf("mathrm mathcal mathit mathtt mathsf mathbf mathdefault")

        space        =(FollowedBy(bslash)
                     +   (Literal(r'\ ')
                       |  Literal(r'\/')
                       |  Literal(r'\,')
                       |  Literal(r'\;')
                       |  Literal(r'\quad')
                       |  Literal(r'\qquad')
                       |  Literal(r'\!')
                       )
                      ).setParseAction(self.space).setName('space')

        customspace  =(Literal(r'\hspace')
                     + (( lbrace
                        + float
                        + rbrace
                       ) | Error(r"Expected \hspace{n}"))
                     ).setParseAction(self.customspace).setName('customspace')

        unicode_range = u"\U00000080-\U0001ffff"
        symbol       =(Regex(UR"([a-zA-Z0-9 +\-*/<>=:,.;!'@()%s])|(\\[%%${}\[\]])" % unicode_range)
                     | Combine(
                         bslash
                       + oneOf(tex2uni.keys())
                       )
                     ).setParseAction(self.symbol).leaveWhitespace()

        c_over_c     =(Suppress(bslash)
                     + oneOf(self._char_over_chars.keys())
                     ).setParseAction(self.char_over_chars)
        
        accent       = Group(
                         Suppress(bslash)
                       + accent
                       + placeable
                     ).setParseAction(self.accent).setName("accent")

        function     =(Suppress(bslash)
                     + function).setParseAction(self.function).setName("function")

        group        = Group(
                         start_group
                       + ZeroOrMore(
                           autoDelim
                         | simple)
                       + end_group
                     ).setParseAction(self.group).setName("group")

        font        <<(Suppress(bslash)
                     + fontname)

        latexfont   <<(Suppress(bslash)
                     + latex2efont)

        frac         = Group(
                       Suppress(
                         bslash
                       + Literal("frac")
                       )
                     + ((group + group)
                        | Error(r"Expected \frac{num}{den}"))
                     ).setParseAction(self.frac).setName("frac")

        sqrt         = Group(
                       Suppress(
                         bslash
                       + Literal("sqrt")
                       )
                     + Optional(
                         Suppress(Literal("["))
                       + Group(
                           OneOrMore(
                             (c_over_c | symbol)
                           ^ font
                           )
                         )
                       + Suppress(Literal("]")),
                         default = None
                       )
                     + (group | Error("Expected \sqrt{value}"))
                     ).setParseAction(self.sqrt).setName("sqrt")

        placeable   <<(accent
                     ^ function
                     ^ (c_over_c | symbol)
                     ^ group
                     ^ frac
                     ^ sqrt
                     ) | Error("Expected symbol or group")

        simple      <<(space
                     | customspace  
                     | font
                     | subsuper
                     )

        subsuperop   =(Literal("_")
                     | Literal("^")
                     )

        subsuper    << Group(
                         ( Optional(placeable)
                         + OneOrMore(
                             subsuperop
                           + placeable
                           )
                         )
                       | placeable
                     )

        ambiDelim    = oneOf(r"""| \| / \backslash \uparrow \downarrow
                                 \updownarrow \Uparrow \Downarrow
                                 \Updownarrow .""")
        leftDelim    = oneOf(r"( [ { \lfloor \langle \lceil")
        rightDelim   = oneOf(r") ] } \rfloor \rangle \rceil")
        autoDelim   <<(Suppress(Literal(r"\left"))
                     + ((leftDelim | ambiDelim) | Error("Expected a delimiter"))
                     + Group(
                         autoDelim
                       ^ OneOrMore(simple))
                     + Suppress(Literal(r"\right"))
                     + ((rightDelim | ambiDelim) | Error("Expected a delimiter"))
                     )

        math         = OneOrMore(
                       autoDelim
                     ^ simple
                     ).setParseAction(self.math).setName("math")

        math_delim   =(~bslash
                     + Literal('$'))

        non_math     = Regex(r"(?:(?:\\[$])|[^$])*"
                     ).setParseAction(self.non_math).setName("non_math").leaveWhitespace()

        self._expression << (
            non_math
          + ZeroOrMore(
                Suppress(math_delim)
              + math
              + (Suppress(math_delim)
                 | Error("Expected end of math '$'"))
              + non_math
            )  
          ) + StringEnd()

        self._expression.enablePackrat()
        
        self.clear()

    def clear(self):
        self._expr = None
        self._state_stack = None
        self._em_width_cache = {}

    def parse(self, s, fonts_object, fontsize, dpi):
        self._state_stack = [self.State(fonts_object, 'default', fontsize, dpi)]
        try:
            self._expression.parseString(s)
        except ParseException, err:
            raise ValueError("\n".join([
                        "",
                        err.line,
                        " " * (err.column - 1) + "^",
                        str(err)]))
        return self._expr

    # The state of the parser is maintained in a stack.  Upon
    # entering and leaving a group { } or math/non-math, the stack
    # is pushed and popped accordingly.  The current state always
    # exists in the top element of the stack.
    class State:
        def __init__(self, font_output, font, fontsize, dpi):
            self.font_output = font_output
            self.font = font
            self.fontsize = fontsize
            self.dpi = dpi

        def copy(self):
            return Parser.State(
                self.font_output,
                self.font,
                self.fontsize,
                self.dpi)

    def get_state(self):
        return self._state_stack[-1]

    def pop_state(self):
        self._state_stack.pop()

    def push_state(self):
        self._state_stack.append(self.get_state().copy())

    def finish(self, s, loc, toks):
        #~ print "finish", toks
        self._expr = Hlist(toks)
        return [self._expr]

    def math(self, s, loc, toks):
        #~ print "math", toks
        hlist = Hlist(toks)
        self.pop_state()
        return [hlist]

    def non_math(self, s, loc, toks):
        #~ print "non_math", toks
        s = toks[0].replace(r'\$', '$')
        symbols = [Char(c, self.get_state()) for c in s]
        hlist = Hlist(symbols)
        # We're going into math now, so set font to 'it'
        self.push_state()
        self.get_state().font = 'it'
        return [hlist]

    def _make_space(self, percentage):
        # All spaces are relative to em width
        state = self.get_state()
        key = (state.font, state.fontsize, state.dpi)
        width = self._em_width_cache.get(key)
        if width is None:
            metrics = state.font_output.get_metrics(
                state.font, 'm', state.fontsize, state.dpi)
            width = metrics.advance
            self._em_width_cache[key] = width
        return Kern(width * percentage)

    _space_widths = { r'\ '      : 0.3,
                      r'\,'      : 0.4,
                      r'\;'      : 0.8,
                      r'\quad'   : 1.6,
                      r'\qquad'  : 3.2,
                      r'\!'      : -0.4,
                      r'\/'      : 0.4 }
    def space(self, s, loc, toks):
        assert(len(toks)==1)
        num = self._space_widths[toks[0]]
        box = self._make_space(num)
        return [box]

    def customspace(self, s, loc, toks):
        return [self._make_space(float(toks[1]))]
    
    def symbol(self, s, loc, toks):
        # print "symbol", toks
        c = toks[0]
        try:
            char = Char(c, self.get_state())
        except ValueError:
            raise ParseFatalException("Unknown symbol: %s" % c)

        if c in self._spaced_symbols:
            return [Hlist( [self._make_space(0.2),
                            char,
                            self._make_space(0.2)] ,
                           do_kern = False)]
        elif c in self._punctuation_symbols:
            return [Hlist( [char,
                            self._make_space(0.2)] ,
                           do_kern = False)]
        return [char]

    _char_over_chars = {
        # The first 2 entires in the tuple are (font, char, sizescale) for
        # the two symbols under and over.  The third element is the space
        # (in multiples of underline height)
        r'AA' : (  ('rm', 'A', 1.0), (None, '\circ', 0.5), 0.0),
    }
    
    def char_over_chars(self, s, loc, toks):
        sym = toks[0]
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)

        under_desc, over_desc, space = \
            self._char_over_chars.get(sym, (None, None, 0.0))
        if under_desc is None:
            raise ParseFatalException("Error parsing symbol")
        
        over_state = state.copy()
        if over_desc[0] is not None:
            over_state.font = over_desc[0]
        over_state.fontsize *= over_desc[2]
        over = Accent(over_desc[1], over_state)

        under_state = state.copy()
        if under_desc[0] is not None:
            under_state.font = under_desc[0]
        under_state.fontsize *= under_desc[2]
        under = Char(under_desc[1], under_state)

        width = max(over.width, under.width)
        
        over_centered = HCentered([over])
        over_centered.hpack(width, 'exactly')

        under_centered = HCentered([under])
        under_centered.hpack(width, 'exactly')
        
        return Vlist([
                over_centered,
                Vbox(0., thickness * space),
                under_centered
                ])
        
    _accent_map = {
        r'hat'   : r'\circumflexaccent',
        r'breve' : r'\combiningbreve',
        r'bar'   : r'\combiningoverline',
        r'grave' : r'\combininggraveaccent',
        r'acute' : r'\combiningacuteaccent',
        r'ddot'  : r'\combiningdiaeresis',
        r'tilde' : r'\combiningtilde',
        r'dot'   : r'\combiningdotabove',
        r'vec'   : r'\combiningrightarrowabove',
        r'"'     : r'\combiningdiaeresis',
        r"`"     : r'\combininggraveaccent',
        r"'"     : r'\combiningacuteaccent',
        r'~'     : r'\combiningtilde',
        r'.'     : r'\combiningdotabove',
        r'^'     : r'\circumflexaccent'
        }

    _wide_accents = Set(r"widehat widetilde".split())

    def accent(self, s, loc, toks):
        assert(len(toks)==1)
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        if len(toks[0]) != 2:
            raise ParseFatalException("Error parsing accent")
        accent, sym = toks[0]
        if accent in self._wide_accents:
            accent = AutoWidthChar(
                '\\' + accent, sym.width, state, char_class=Accent)
        else:
            accent = Accent(self._accent_map[accent], state)
        centered = HCentered([accent])
        centered.hpack(sym.width, 'exactly')
        return Vlist([
                centered,
                Vbox(0., thickness * 2.0),
                Hlist([sym])
                ])

    def function(self, s, loc, toks):
        #~ print "function", toks
        self.push_state()
        state = self.get_state()
        state.font = 'rm'
        hlist = Hlist([Char(c, state) for c in toks[0]])
        self.pop_state()
        hlist.function_name = toks[0]
        return hlist

    def start_group(self, s, loc, toks):
        self.push_state()
        # Deal with LaTeX-style font tokens
        if len(toks):
            self.get_state().font = toks[0][4:]
        return []

    def group(self, s, loc, toks):
        grp = Hlist(toks[0])
        return [grp]

    def end_group(self, s, loc, toks):
        self.pop_state()
        return []

    def font(self, s, loc, toks):
        assert(len(toks)==1)
        name = toks[0]
        self.get_state().font = name
        return []

    def is_overunder(self, nucleus):
        if isinstance(nucleus, Char):
            return nucleus.c in self._overunder_symbols
        elif isinstance(nucleus, Hlist) and hasattr(nucleus, 'function_name'):
            return nucleus.function_name in self._overunder_functions
        return False

    def is_dropsub(self, nucleus):
        if isinstance(nucleus, Char):
            return nucleus.c in self._dropsub_symbols
        return False

    def is_slanted(self, nucleus):
        if isinstance(nucleus, Char):
            return nucleus.is_slanted()
        return False

    def subsuperscript(self, s, loc, toks):
        assert(len(toks)==1)
        # print 'subsuperscript', toks

        nucleus = None
        sub = None
        super = None

        if len(toks[0]) == 1:
            return toks[0].asList()
        elif len(toks[0]) == 2:
            op, next = toks[0]
            nucleus = Hbox(0.0)
            if op == '_':
                sub = next
            else:
                super = next
        elif len(toks[0]) == 3:
            nucleus, op, next = toks[0]
            if op == '_':
                sub = next
            else:
                super = next
        elif len(toks[0]) == 5:
            nucleus, op1, next1, op2, next2 = toks[0]
            if op1 == op2:
                if op1 == '_':
                    raise ParseFatalException("Double subscript")
                else:
                    raise ParseFatalException("Double superscript")
            if op1 == '_':
                sub = next1
                super = next2
            else:
                super = next1
                sub = next2
        else:
            raise ParseFatalException("Subscript/superscript sequence is too long.  Use braces { } to remove ambiguity.")

        state = self.get_state()
        rule_thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        xHeight = state.font_output.get_xheight(
            state.font, state.fontsize, state.dpi)

        if self.is_overunder(nucleus):
            vlist = []
            shift = 0.
            width = nucleus.width
            if super is not None:
                super.shrink()
                width = max(width, super.width)
            if sub is not None:
                sub.shrink()
                width = max(width, sub.width)

            if super is not None:
                hlist = HCentered([super])
                hlist.hpack(width, 'exactly')
                vlist.extend([hlist, Kern(rule_thickness * 2.0)])
            hlist = HCentered([nucleus])
            hlist.hpack(width, 'exactly')
            vlist.append(hlist)
            if sub is not None:
                hlist = HCentered([sub])
                hlist.hpack(width, 'exactly')
                vlist.extend([Kern(rule_thickness * 2.0), hlist])
                shift = hlist.height + hlist.depth + rule_thickness * 2.0
            vlist = Vlist(vlist)
            vlist.shift_amount = shift + nucleus.depth * 0.5
            result = Hlist([vlist])
            return [result]

        shift_up = nucleus.height - SUBDROP * xHeight
        if self.is_dropsub(nucleus):
            shift_down = nucleus.depth + SUBDROP * xHeight
        else:
            shift_down = SUBDROP * xHeight
        if super is None:
            # @757
            sub.shrink()
            x = Hlist([sub])
            # x.width += SCRIPT_SPACE * xHeight
            shift_down = max(shift_down, SUB1)
            clr = x.height - (abs(xHeight * 4.0) / 5.0)
            shift_down = max(shift_down, clr)
            x.shift_amount = shift_down
        else:
            super.shrink()
            x = Hlist([super, Kern(SCRIPT_SPACE * xHeight)])
            # x.width += SCRIPT_SPACE * xHeight
            clr = SUP1 * xHeight
            shift_up = max(shift_up, clr)
            clr = x.depth + (abs(xHeight) / 4.0)
            shift_up = max(shift_up, clr)
            if sub is None:
                x.shift_amount = -shift_up
            else: # Both sub and superscript
                sub.shrink()
                y = Hlist([sub])
                # y.width += SCRIPT_SPACE * xHeight
                shift_down = max(shift_down, SUB1 * xHeight)
                clr = (2.0 * rule_thickness -
                       ((shift_up - x.depth) - (y.height - shift_down)))
                if clr > 0.:
                    shift_up += clr
                    shift_down += clr
                if self.is_slanted(nucleus):
                    x.shift_amount = DELTA * (shift_up + shift_down)
                x = Vlist([x,
                           Kern((shift_up - x.depth) - (y.height - shift_down)),
                           y])
                x.shift_amount = shift_down

        result = Hlist([nucleus, x])
        return [result]

    def frac(self, s, loc, toks):
        assert(len(toks)==1)
        assert(len(toks[0])==2)
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)

        num, den = toks[0]
        num.shrink()
        den.shrink()
        cnum = HCentered([num])
        cden = HCentered([den])
        width = max(num.width, den.width) + thickness * 10.
        cnum.hpack(width, 'exactly')
        cden.hpack(width, 'exactly')
        vlist = Vlist([cnum,                      # numerator
                       Vbox(0, thickness * 2.0),  # space
                       Hrule(state),              # rule
                       Vbox(0, thickness * 4.0),  # space
                       cden                       # denominator
                       ])

        # Shift so the fraction line sits in the middle of the
        # equals sign
        metrics = state.font_output.get_metrics(
            state.font, '=', state.fontsize, state.dpi)
        shift = (cden.height -
                 ((metrics.ymax + metrics.ymin) / 2 -
                  thickness * 3.0))
        vlist.shift_amount = shift

        hlist = Hlist([vlist, Hbox(thickness * 2.)])
        return [hlist]

    def sqrt(self, s, loc, toks):
        #~ print "sqrt", toks
        root, body = toks[0]
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)

        if root is None:
            root = Box(0., 0., 0.)
        else:
            if not isinstance(root, ParseResults):
                raise ParseFatalException(
                    "Can not parse root of radical. "
                    "Only simple symbols are allowed in the root.")
            root = Hlist(root.asList())
            root.shrink()
            root.shrink()

        # Determine the height of the body, and add a little extra to
        # the height so it doesn't seem cramped
        height = body.height - body.shift_amount + thickness * 5.0
        depth = body.depth + body.shift_amount
        check = AutoHeightChar(r'\__sqrt__', height, depth, state, always=True)
        height = check.height - check.shift_amount
        depth = check.depth + check.shift_amount

        # Put a little extra space to the left and right of the body
        padded_body = Hlist([Hbox(thickness * 2.0),
                             body,
                             Hbox(thickness * 2.0)])
        rightside = Vlist([Hrule(state),
                           Fill(),
                           padded_body])
        # Stretch the glue between the hrule and the body
        rightside.vpack(height + 1.0, depth, 'exactly')

        # Add the root and shift it upward so it is above the tick.
        # The value of 0.6 is a hard-coded hack ;)
        root_vlist = Vlist([Hlist([root])])
        root_vlist.shift_amount = -height * 0.6

        hlist = Hlist([root_vlist,               # Root
                       # Negative kerning to put root over tick
                       Kern(-check.width * 0.5),
                       check,                    # Check
                       rightside])               # Body
        return [hlist]

    def auto_sized_delimiter(self, s, loc, toks):
        #~ print "auto_sized_delimiter", toks
        front, middle, back = toks
        state = self.get_state()
        height = max([x.height for x in middle])
        depth = max([x.depth for x in middle])
        parts = []
        # \left. and \right. aren't supposed to produce any symbols
        if front != '.':
            parts.append(AutoHeightChar(front, height, depth, state))
        parts.extend(middle.asList())
        if back != '.':
            parts.append(AutoHeightChar(back, height, depth, state))
        hlist = Hlist(parts)
        return hlist

####

##############################################################################
# MAIN

class MathTextParser(object):
    """
    Parse the math expression s, return the (bbox, fonts) tuple needed
    to render it.

    fontsize must be in points

    return is width, height, fonts
    """
    _parser = None
    
    _backend_mapping = {
        'Bitmap': MathtextBackendBitmap,
        'Agg'   : MathtextBackendAgg,
        'PS'    : MathtextBackendPs,
        'Pdf'   : MathtextBackendPdf,
        'SVG'   : MathtextBackendSvg,
        'Cairo' : MathtextBackendCairo
        }

    def __init__(self, output):
        self._output = output
        self._cache = {}

    def parse(self, s, dpi = 72, prop = None):
        if prop is None:
            prop = FontProperties()
        
        cacheKey = (s, dpi, hash(prop))
        result = self._cache.get(cacheKey)
        if result is not None:
            return result

        if self._output == 'PS' and rcParams['ps.useafm']:
            font_output = StandardPsFonts(prop)
        else:
            backend = self._backend_mapping[self._output]()
            fontset = rcParams['mathtext.fontset']
            if fontset == 'cm':
                font_output = BakomaFonts(prop, backend)
            elif fontset == 'stix':
                font_output = StixFonts(prop, backend)
            elif fontset == 'custom':
                font_output = UnicodeFonts(prop, backend)
            else:
                raise ValueError("mathtext.fontset must be either 'cm', 'stix', or 'custom'")

        fontsize = prop.get_size_in_points()

        # This is a class variable so we don't rebuild the parser
        # with each request.
        if self._parser is None:
            self.__class__._parser = Parser()
            
        box = self._parser.parse(s, font_output, fontsize, dpi)
        font_output.set_canvas_size(box.width, box.height, box.depth)
        result = font_output.get_results(box)
        self._cache[cacheKey] = result
        # Free up the transient data structures
        self._parser.clear()

        # Fix cyclical references
        font_output.destroy()
        font_output.mathtext_backend.fonts_object = None
        font_output.mathtext_backend = None
        
        return result
