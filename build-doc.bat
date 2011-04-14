SET VERSION=1.7
python setup.py build_sphinx
rem python setup.py build_sphinx -b latex

rem pushd build\sphinx\latex
rem pdflatex pyreadline.tex
rem pdflatex pyreadline.tex
rem pdflatex pyreadline.tex
rem popd

mkdir dist
copy build\sphinx\latex\pyreadline.pdf dist\pyreadline-%VERSION%.pdf

xcopy /S /I build\sphinx\html dist\pyreadline-htmldoc-%VERSION%
