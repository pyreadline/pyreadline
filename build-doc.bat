SET VERSION=1.7
python setup.py build_sphinx
python setup.py build_sphinx -b latex

pushd build\sphinx\latex
pdflatex pyreadline.tex
pdflatex pyreadline.tex
pdflatex pyreadline.tex
popd

mkdir dist
copy build\sphinx\latex\pyreadline.pdf dist\pyreadline-%VERSION%.pdf

xcopy /S /I build\sphinx\html dist\pyreadline-htmldoc-%VERSION%
