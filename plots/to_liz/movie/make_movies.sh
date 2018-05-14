echo $1
pdfcrop sd-tec-movie.pdf
mv sd-tec-movie-crop.pdf sd-tec-movie.pdf
pdftocairo -png sd-tec-movie.pdf
convert -delay 100 frames -loop 0 sd-tec-movie-*.png sd-tec-movie.gif
rm *.png