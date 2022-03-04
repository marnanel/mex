import mex.state
import pytest

KEYWORDS=[
        'above', 'abovedisplayshortskip', 'abovedisplayskip',
        'abovewithdelims', 'accent', 'adjdemerits', 'advance',
        'afterassignment', 'aftergroup', 'atop', 'atopwithdelims', 'badness',
        'baselineskip', 'batchmode', 'begingroup', 'belowdisplayshortskip',
        'belowdisplayskip', 'binoppenalty', 'botmark', 'box', 'boxmaxdepth',
        'brokenpenalty', 'catcode', 'char', 'chardef', 'cleaders', 'closein',
        'closeout', 'clubpenalty', 'copy', 'countdef', 'cr', 'crcr',
        'csname', 'day', 'deadcycles', 'def', 'defaulthyphenchar',
        'defaultskewchar', 'delcode', 'delimiter', 'delimiterfactor',
        'delimitershortfall', 'dimendef', 'discretionary', 'displayindent',
        'displaylimits', 'displaystyle', 'displaywidowpenalty',
        'displaywidth', 'divide', 'doublehyphendemerits', 'dp', 'dump',
        'edef', 'else', 'emergencystretch', 'end', 'endcsname', 'endgroup',
        'endinput', 'endlinechar', 'eqno', 'errhelp', 'errmessage',
        'errorcontextlines', 'errorstopmode', 'escapechar', 'everycr',
        'everydisplay', 'everyhbox', 'everyjob', 'everymath', 'everypar',
        'everyvbox', 'exhyphenpenalty', 'expandafter', 'fam', 'fi',
        'finalhyphendemerits', 'firstmark', 'floatingpenalty', 'font',
        'fontdimen', 'fontname', 'futurelet', 'gdef', 'global', 'globaldefs',
        'halign', 'hangafter', 'hangindent', 'hbadness', 'hbox', 'hfil',
        'hfill', 'hfilneg', 'hfuzz', 'hoffset', 'holdinginserts', 'hrule',
        'hsize', 'hskip', 'hss', 'ht', 'hyphenation', 'hyphenchar',
        'hyphenpenalty', 'if', 'ifcase', 'ifcat', 'ifdim', 'ifeof',
        'iffalse', 'ifhbox', 'ifhmode', 'ifinner', 'ifmmode', 'ifnum',
        'ifodd', 'iftrue', 'ifvbox', 'ifvmode', 'ifvoid', 'ifx',
        'ignorespaces', 'immediate', 'indent', 'input', 'inputlineno',
        'insert', 'insertpenalties', 'interlinepenalty', 'jobname', 'kern',
        'language', 'lastbox', 'lastkern', 'lastpenalty', 'lastskip',
        'lccode', 'leaders', 'left', 'lefthyphenmin', 'leftskip', 'leqno',
        'let', 'limits', 'linepenalty', 'lineskip', 'lineskiplimit', 'long',
        'looseness', 'lower', 'lowercase', 'mag', 'mark', 'mathaccent',
        'mathbin', 'mathchar', 'mathchardef', 'mathchoice', 'mathclose',
        'mathcode', 'mathinner', 'mathop', 'mathopen', 'mathord',
        'mathpunct', 'mathrel', 'mathsurround', 'maxdeadcycles', 'maxdepth',
        'meaning', 'medmuskip', 'message', 'mkern', 'month', 'moveleft',
        'moveright', 'mskip', 'multiply', 'muskipdef', 'newlinechar',
        'noalign', 'noboundary', 'noexpand', 'noindent', 'nolimits',
        'nonscript', 'nonstopmode', 'nulldelimiterspace', 'nullfont',
        'number', 'omit', 'openin', 'openout', 'or', 'outer', 'output',
        'outputpenalty', 'over', 'overfullrule', 'overline',
        'overwithdelims', 'pagedepth', 'pagefilllstretch', 'pagefillstretch',
        'pagefilstretch', 'pagegoal', 'pageshrink', 'pagestretch',
        'pagetotal', 'par', 'parfillskip', 'parindent', 'parshape',
        'parskip', 'patterns', 'pausing', 'penalty', 'postdisplaypenalty',
        'predisplaypenalty', 'predisplaysize', 'pretolerance', 'prevdepth',
        'prevgraf', 'radical', 'raise', 'read', 'relax', 'relpenalty',
        'right', 'righthyphenmin', 'rightskip', 'romannumeral', 'scriptfont',
        'scriptscriptfont', 'scriptscriptstyle', 'scriptspace',
        'scriptstyle', 'scrollmode', 'setbox', 'setlanguage', 'sfcode',
        'shipout', 'show', 'showbox', 'showboxbreadth', 'showboxdepth',
        'showlists', 'showthe', 'skewchar', 'skipdef', 'spacefactor',
        'spaceskip', 'span', 'special', 'splitbotmark', 'splitfirstmark',
        'splitmaxdepth', 'splittopskip', 'string', 'tabskip', 'textfont',
        'textstyle', 'the', 'thickmuskip', 'thinmuskip', 'time', 'toks',
        'toksdef', 'tolerance', 'topmark', 'topskip', 'tracingcommands',
        'tracinglostchars', 'tracingmacros', 'tracingonline',
        'tracingoutput', 'tracingpages', 'tracingparagraphs',
        'tracingrestores', 'tracingstats', 'uccode', 'uchyph', 'underline',
        'unhbox', 'unhcopy', 'unkern', 'unpenalty', 'unskip', 'unvbox',
        'unvcopy', 'uppercase', 'vadjust', 'valign', 'vbadness', 'vbox',
        'vcenter', 'vfil', 'vfill', 'vfilneg', 'vfuzz', 'voffset', 'vrule',
        'vsize', 'vskip', 'vsplit', 'vss', 'vtop', 'wd', 'widowpenalty',
        'write', 'xdef', 'xleaders', 'xspaceskip', 'year',
        ]

if __name__=='__main__':
    count = 0
    s = mex.state.State()

    for k in KEYWORDS:
        result = s.get(k,
                the_object_itself=True)
        print(k, result)
        if result is not None:
            count += 1

    print()
    print('Keywords:', len(KEYWORDS))
    print('Found: %d (%g%%)' % (
        count,
        (count/len(KEYWORDS))*100
        ))
